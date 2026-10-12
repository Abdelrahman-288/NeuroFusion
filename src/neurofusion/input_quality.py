"""Deterministic input checks, not a learned modality or diagnostic validator."""
from pathlib import Path
import numpy as np
import nibabel as nib
from PIL import Image, UnidentifiedImageError


class InputQualityError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__('Input rejected: ' + '; '.join(report['errors']))


def inspect_input(path, task):
    path = Path(path)
    report = {'policy_version': 1, 'task': task, 'status': 'accepted_with_warnings',
              'modality_verified': False, 'metrics': {}, 'errors': [],
              'warnings': ['Modality and anatomy are not automatically verified. Confirm the selected task and sequence.'],
              'scope': 'Technical checks and heuristic warnings only; passing does not establish medical suitability.'}
    metrics, errors, warnings = report['metrics'], report['errors'], report['warnings']
    try:
        if task == 'tumor-image':
            if path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
                raise ValueError('Tumor input must be PNG or JPEG')
            with Image.open(path) as image:
                if image.format not in ('PNG', 'JPEG'):
                    raise ValueError('File content must be PNG or JPEG')
                if min(image.size) < 32 or image.width * image.height > 4000000:
                    raise ValueError('Image must be at least 32 pixels per side and at most 4 million pixels')
                if getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Multi-frame images are unsupported')
                if 'A' in image.getbands() or 'transparency' in image.info:
                    if np.asarray(image.convert('RGBA'))[:, :, 3].min() < 255:
                        raise ValueError('Transparent pixels are unsupported; supply an opaque MRI image')
                rgb = np.asarray(image.convert('RGB'), dtype=np.float32)
                gray = np.asarray(image.convert('L'), dtype=np.float32)
                p1, p99 = np.percentile(gray, [1, 99])
                metrics.update(width=image.width, height=image.height, source_mode=image.mode,
                               grayscale_std=float(gray.std()), percentile_range_1_99=float(p99-p1))
                if gray.std() < 1e-8:
                    raise ValueError('Image has no grayscale intensity variation')
                if p99-p1 < 10 or gray.std() < 2:
                    warnings.append('Low grayscale contrast by heuristic thresholds; inspect the source image.')
                color_fraction = float((np.ptp(rgb, axis=2) > 10).mean())
                metrics['color_pixel_fraction'] = color_fraction
                if color_fraction > .05:
                    warnings.append('Substantial color content; model preprocessing discards color. Check for overlays or a non-MRI image.')
                if min(image.size) < 128:
                    warnings.append('Input is smaller than the 128-pixel model grid and will be enlarged.')
                if max(image.size)/min(image.size) > 2:
                    warnings.append('Unusual aspect ratio; resizing to the square model grid distorts proportions.')
        elif task == 'stroke-dwi':
            if not path.name.lower().endswith(('.nii', '.nii.gz')):
                raise ValueError('DWI input must be a NIfTI .nii or .nii.gz file')
            image = nib.load(path)
            if len(image.shape) != 3 or min(image.shape) < 1 or max(image.shape) > 512 or np.prod(image.shape) > 16000000:
                raise ValueError('Expected 3D volume, at most 512 per axis and 16 million voxels')
            if image.header.get_xyzt_units()[0] != 'mm':
                raise ValueError('DWI spatial units must be millimeters')
            affine = image.affine
            if not np.isfinite(affine).all() or abs(np.linalg.det(affine[:3,:3])) < 1e-8:
                raise ValueError('DWI geometry must be finite and invertible')
            values = image.get_fdata(dtype=np.float32)
            if not np.isfinite(values).all():
                raise ValueError('DWI contains nonfinite intensities')
            nonzero = values[values != 0]
            if not nonzero.size or nonzero.std() < 1e-8 or not np.isfinite(nonzero.std()):
                raise ValueError('DWI requires finite, varying nonzero intensities')
            spacing = np.linalg.norm(affine[:3,:3], axis=0)
            metrics.update(shape=list(image.shape), voxel_spacing_mm=spacing.tolist(),
                           nonzero_fraction=float(nonzero.size/values.size), nonzero_std=float(nonzero.std()),
                           orientation=''.join(nib.aff2axcodes(affine)))
            if spacing.max()/spacing.min() > 4:
                warnings.append('Strongly anisotropic voxels; the current model does not resample spacing.')
            if spacing.min() < .2 or spacing.max() > 10:
                warnings.append('Unusual voxel spacing by heuristic thresholds; verify acquisition geometry.')
            axes = affine[:3,:3]/spacing
            if np.max(np.abs(axes.T@axes-np.eye(3))) > .01:
                warnings.append('Sheared geometry detected; previews are voxel-based and no geometric resampling is performed.')
            if min(image.shape) < 16:
                warnings.append('Small volume dimension; confirm that this is a complete intended acquisition.')
        else:
            raise ValueError('Unsupported task')
    except (ValueError, OSError, UnidentifiedImageError, nib.filebasedimages.ImageFileError) as error:
        # Do not return file-system paths or decoder internals to the browser.
        message = str(error) if type(error) is ValueError else 'File could not be decoded as the selected input type'
        errors.append(message)
    if errors:
        report['status'] = 'rejected'
    return report


def require_input_quality(path, task):
    report = inspect_input(path, task)
    if report['errors']:
        raise InputQualityError(report)
    return report
