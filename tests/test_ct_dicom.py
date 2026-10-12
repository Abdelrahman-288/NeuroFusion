import numpy as np
import pytest
from neurofusion.specialist_inputs import ct_windows


def test_ct_hu_rescale_and_patient_identity(tmp_path):
    pydicom=pytest.importorskip('pydicom')
    from pydicom.dataset import FileDataset,FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian,generate_uid
    meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian
    ds=FileDataset(str(tmp_path/'a.dcm'),{},file_meta=meta,preamble=b'\0'*128)
    ds.Modality='CT';ds.PhotometricInterpretation='MONOCHROME2';ds.PatientID='synthetic'
    ds.StudyInstanceUID=generate_uid();ds.SeriesInstanceUID=generate_uid()
    ds.RescaleSlope=2;ds.RescaleIntercept=-1000;ds.Rows=2;ds.Columns=2;ds.SamplesPerPixel=1
    ds.BitsAllocated=16;ds.BitsStored=16;ds.HighBit=15;ds.PixelRepresentation=1
    ds.PixelData=np.array([[500,520],[540,560]],dtype='<i2').tobytes();ds.save_as(ds.filename)
    windows,info=ct_windows(ds.filename)
    assert windows.shape==(3,2,2) and windows[0,0,1]==pytest.approx(.5)
    assert info['patient_id']=='synthetic'
    ds.Modality='MR';ds.save_as(ds.filename)
    with pytest.raises(ValueError):ct_windows(ds.filename)
