"""Local, label-free inference with explicit tasks and a common result schema."""
from pathlib import Path
import numpy as np
from PIL import Image
import nibabel as nib
from nibabel.orientations import io_orientation,ornt_transform,axcodes2ornt
import torch
from neurofusion.cohort import digest
from neurofusion.data import save_json
from neurofusion.tumor import TumorCNN,CLASSES
from neurofusion.tumor_segmentation import TumorUNet,native_probability
from neurofusion.segmentation import CompactUNet,predict_volume
from neurofusion.preprocessing import restore_prediction
from neurofusion.input_quality import require_input_quality
from neurofusion.model_registry import active_models
from neurofusion.uncertainty_policy import uncertainty_decision
from neurofusion.measurements import measure_regions,bind_evidence,validate_evidence

MODELS={
    'tumor_classifier':('experiments/tumor-cnn-002/last.pt','41bce20f491d345adeac31341b0f6a4ccf8908383bcf76e583962a5989180235'),
    'tumor_segmenter':('experiments/tumor-seg-001/last.pt','8647d9b544d1528cdf15224b72e55b7927b166a6ccd7213b3d85c4fa442a6f21'),
    'stroke_dwi':('experiments/dwi-component-001/last.pt','03a77f768e57cc2eb38a0db26d615d626a1e815f2fef5d1647bab350f18e36ff')}


def load_model_checkpoint(key,path,expected):
    if digest(path)!=expected: raise ValueError('Registered model checksum mismatch')
    model={'tumor_classifier':TumorCNN,'tumor_segmenter':TumorUNet,'stroke_dwi':CompactUNet}[key]()
    with torch.serialization.safe_globals([np._core.multiarray.scalar,np.dtype,np.dtypes.Float64DType,np.dtypes.Float32DType]):
        checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    model.load_state_dict(checkpoint['model'])
    if any(not torch.isfinite(p).all() for p in model.state_dict().values()):
        raise ValueError('Nonfinite checkpoint weights')
    return model


def prepare_dwi_input(path):
    image=nib.load(path)
    if len(image.shape)!=3 or max(image.shape)>512 or np.prod(image.shape)>16000000:
        raise ValueError('Expected a 3D DWI volume, at most 512 voxels per axis and 16 million total')
    if image.header.get_xyzt_units()[0]!='mm' or not np.isfinite(image.affine).all() or abs(np.linalg.det(image.affine[:3,:3]))<1e-8:
        raise ValueError('DWI requires valid physical geometry and millimeter units')
    canonical=nib.as_closest_canonical(image)
    values=canonical.get_fdata(dtype=np.float32)
    if not np.isfinite(values).all(): raise ValueError('Nonfinite DWI intensities')
    selected=values[values!=0]
    if not len(selected) or selected.std()<1e-8: raise ValueError('DWI intensity variation required')
    normalized=np.zeros_like(values); normalized[values!=0]=(selected-selected.mean())/selected.std()
    metadata={'original_shape':list(image.shape),'original_affine':image.affine.tolist(),
        'canonical_shape':list(canonical.shape),'canonical_affine':canonical.affine.tolist(),
        'inverse_orientation':ornt_transform(axcodes2ornt(('R','A','S')),io_orientation(image.affine)).tolist(),
        'xyzt_units':list(image.header.get_xyzt_units())}
    return normalized,metadata


class Predictor:
    def __init__(self,project,device=None):
        self.project=Path(project).resolve()
        self.device=device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.models={}
        self.registry=None
        torch.set_num_threads(2)

    def model(self,key):
        if self.registry is None:
            self.registry=active_models(self.project,MODELS)
        if key not in self.models:
            relative,expected=self.registry[key]; path=self.project/relative
            model=load_model_checkpoint(key,path,expected)
            self.models[key]=model.to(self.device).eval()
        return self.models[key]

    @torch.inference_mode()
    def analyze(self,path,task,output):
        path=Path(path); output=Path(output)
        if task not in ['tumor-image','stroke-dwi']: raise ValueError('Unsupported task')
        if output.exists(): raise ValueError('Choose a new result folder')
        quality=require_input_quality(path,task)
        result={'schema_version':1,'task':task,'input_sha256':digest(path),'device':self.device,
            'input_quality':quality,
            'research_only':True,'input_compatibility':'User-selected modality; not automatically verified',
            'threshold':.5,'models':{},'views':[],
            'limitations':['Predictions are uncalibrated research outputs, not diagnoses.','No reference labels are used during inference.']}
        if task=='tumor-image':
            if path.suffix.lower() not in ['.png','.jpg','.jpeg']: raise ValueError('Tumor input must be PNG or JPEG')
            with Image.open(path) as image:
                if image.width*image.height>4000000 or min(image.size)<32: raise ValueError('Image size must be at least 32px and at most 4 million pixels')
                if image.format not in ['PNG','JPEG']: raise ValueError('Expected PNG or JPEG content')
                plain=np.asarray(image.convert('RGB')).copy()
                values=np.asarray(image.convert('L').resize((128,128),Image.Resampling.BILINEAR)).copy()
            tensor=torch.from_numpy(values)[None,None].to(self.device).float()/255
            scores=self.model('tumor_classifier')(tensor).softmax(1)[0].cpu().numpy()
            probability=self.model('tumor_segmenter')(tensor).sigmoid()[0,0].cpu().numpy()
            probability=native_probability(probability,plain.shape[:2])
            result['classification']={'predicted_class':CLASSES[int(scores.argmax())],
                'scores':{c:float(s) for c,s in zip(CLASSES,scores)},'calibrated':False}
            result['limitations']+=['No_tumor does not mean healthy.','Segmentation was evaluated only on tumor-positive BRISC images.','Classification and segmentation are separate models; neither validates or suppresses the other.']
            result['models']={key:self.registry[key][1] for key in ['tumor_classifier','tumor_segmenter']}
            output.mkdir(parents=True)
            np.savez_compressed(output/'probability.npz',probability=probability)
            result['probability_file']='probability.npz'
            self.view(output,plain,probability>=.5,0,result)
        else:
            if not (path.name.lower().endswith('.nii.gz') or path.suffix.lower()=='.nii'): raise ValueError('DWI input must be NIfTI .nii or .nii.gz')
            values,metadata=prepare_dwi_input(path)
            probability=predict_volume(self.model('stroke_dwi'),values,self.device)
            result['models']={'stroke_dwi':self.registry['stroke_dwi'][1]}
            result['limitations']+=['DWI sequence must be supplied explicitly; this is not a generic MRI or CT model.',
                                    'Viewer uses canonical RAS slices; displayed proportions are voxel-based.']
            output.mkdir(parents=True)
            restore_prediction(probability,metadata,output/'probability.nii.gz')
            result['probability_file']='probability.nii.gz'
            result['native_geometry']=metadata
            lo,hi=np.percentile(values[values!=0],[1,99])
            for z in range(values.shape[2]):
                gray=(np.clip((np.rot90(values[:,:,z])-lo)/max(hi-lo,1e-8),0,1)*255).astype(np.uint8)
                self.view(output,np.repeat(gray[:,:,None],3,axis=2),np.rot90(probability[:,:,z]>=.5),z,result)
            result['initial_slice']=int(np.argmax((probability>=.5).sum(axis=(0,1))))
        result['predicted_pixels_or_voxels']=int((probability>=.5).sum())
        result['measurements']=bind_evidence(measure_regions(probability,metadata if task=='stroke-dwi' else None),result,output)
        result['measurement_verification']=validate_evidence(result,output)
        result['uncertainty']=uncertainty_decision(task,result['models'],scores if task=='tumor-image' else None)
        save_json(output/'result.json',result)
        return result

    @staticmethod
    def view(output,plain,mask,index,result):
        name=f'image-{index:03d}.png'; overlay=f'overlay-{index:03d}.png'
        Image.fromarray(plain).save(output/name)
        rgba=np.zeros((*mask.shape,4),dtype=np.uint8); rgba[mask]=[255,80,80,180]
        Image.fromarray(rgba).save(output/overlay)
        result['views'].append({'slice':index,'image':name,'overlay':overlay})
