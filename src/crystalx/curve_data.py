"""Qt-independent XY series and labels shared by diffraction and AFM exports."""
from dataclasses import dataclass,field

@dataclass
class XYScan:
    x: list
    intensity: list
    metadata: dict=field(default_factory=dict)
    attenuation: list=field(default_factory=list)

    @property
    def data_kind(self): return self.metadata.get('DATA_KIND','XRD')

    @property
    def template_name(self):
        if self.data_kind=='AFM': return 'AFM'
        if self.data_kind=='XY': return 'global'
        axis=self.metadata.get('MEAS_SCAN_AXIS_X_INTERNAL','').lower().replace('_','')
        # RAS has no mandatory experiment-kind field. Prefer explicit metadata.
        kind=' '.join(self.metadata.get(k,'') for k in ('MEASUREMENT_TYPE','EXPERIMENT_TYPE','MEAS_TYPE','FILE_COMMENT')).lower()
        if 'rocking' in kind or axis=='omega': return 'Rocking Curve'
        if 'reflectivity' in kind or 'xrr' in kind: return 'XRR'
        if axis in ('twothetaomega','twothetatheta','omegatwotheta','2theta','twotheta'):
            return 'XRR' if self.x and min(self.x)>=0 and max(self.x)<=10 else 'XRD'
        if 'diffraction' in kind or 'xrd' in kind: return 'XRD'
        return 'global'

    @property
    def axis_label(self):
        if 'PLOT_X_LABEL' in self.metadata: return self.metadata['PLOT_X_LABEL']
        axis=self.metadata.get('MEAS_SCAN_AXIS_X_INTERNAL','2θ')
        if axis.lower().replace('_','') in ('2theta','twotheta','twothetaomega'): axis='2θ'
        if axis.lower()=='omega': axis='ω'
        unit=self.metadata.get('MEAS_SCAN_UNIT_X','deg')
        return f'{axis} ({"°" if unit.lower()=="deg" else unit})'

    @property
    def y_label(self):
        return self.metadata.get('PLOT_Y_LABEL','Intensity'+(' ('+self.metadata['MEAS_SCAN_UNIT_Y']+')' if self.metadata.get('MEAS_SCAN_UNIT_Y') else ''))
