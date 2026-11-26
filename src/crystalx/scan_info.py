"""Measured scan information and frequency-weighted AFM histogram statistics."""
import numpy as np

def afm_statistics(scan):
    x=np.asarray(scan.x,dtype=float); weights=np.asarray(scan.intensity,dtype=float); total=float(weights.sum())
    if total<=0: raise ValueError('像素总数为0，无法计算加权统计。')
    mean=float(np.dot(x,weights)/total); variance=float(np.dot((x-mean)**2,weights)/total)
    order=np.argsort(x); cumulative=np.cumsum(weights[order]); median=float(x[order[np.searchsorted(cumulative,total/2)]])
    mode=int(np.argmax(weights)); occupied=x[weights>0]
    return {'mean':mean,'mode':float(x[mode]),'max_count':float(weights[mode]),'variance':variance,
            'std':variance**.5,'ra':float(np.dot(np.abs(x-mean),weights)/total),'median':median,
            'minimum':float(occupied.min()),'maximum':float(occupied.max()),'pixels':total,'bins':len(x)}

def scan_information(scan):
    m=scan.metadata
    rows=[('数据点数',str(len(scan.x))),('横轴',scan.axis_label),('纵轴',scan.y_label)]
    if scan.data_kind=='AFM':
        if m.get('AFM_TYPE')=='profile':
            heights=np.asarray(scan.intensity,dtype=float); mean=float(heights.mean()); variance=float(heights.var())
            unit=scan.y_label.split('(')[-1].rstrip(')')
            rows.extend((label,f'{value:.9g} {suffix}') for label,value,suffix in (
                ('平均高度',mean,unit),('最低高度',float(heights.min()),unit),('最高高度',float(heights.max()),unit),
                ('峰谷高度差',float(np.ptp(heights)),unit),('方差',variance,unit+'²'),
                ('标准差 / Rq（估计）',variance**.5,unit),('Ra（估计）',float(np.abs(heights-mean).mean()),unit)))
            return rows+[('统计说明','按剖面采样点计算，相对平均高度估计Ra/Rq；不代表整个面域。')]
        try: stats=afm_statistics(scan)
        except ValueError as error: return rows+[('统计说明',str(error))]
        unit=scan.axis_label.split('(')[-1].rstrip(')')
        for key,label,suffix in [('pixels','像素总数',''),('mean','平均高度',unit),('mode','峰值高度（众数）',unit),
                ('max_count','峰值频数','pixels'),('median','中位高度',unit),('variance','方差',unit+'²'),
                ('std','标准差 / Rq（估计）',unit),('ra','Ra（估计）',unit),('minimum','最低有效高度',unit),('maximum','最高有效高度',unit)]:
            rows.append((label,f'{stats[key]:.9g} {suffix}'.strip()))
        return rows+[('统计说明','按高度分箱及像素数加权估计；不是对原始二维形貌的重新计算。')]
    rows.append(('扫描范围',f'{min(scan.x):.9g} — {max(scan.x):.9g}'))
    if len(scan.x)>1: rows.append(('采样间距（中位数）',f'{np.median(np.abs(np.diff(scan.x))):.9g}'))
    for key,label in [('MEAS_SCAN_AXIS_X_INTERNAL','扫描轴'),('MEAS_SCAN_MODE','扫描模式'),('MEAS_SCAN_START_TIME','开始时间'),
            ('MEAS_SCAN_END_TIME','结束时间'),('MEAS_SCAN_SPEED','扫描速度'),('MEAS_SCAN_SPEED_UNIT','速度单位'),
            ('FILE_SYSTEM_NAME','测量系统'),('HW_XG_TARGET_NAME','靶材'),('HW_XG_WAVE_LENGTH_ALPHA1','Kα₁ 波长'),
            ('HW_XG_WAVE_LENGTH_ALPHA2','Kα₂ 波长'),('HW_XG_WAVE_LENGTH_UNIT','波长单位'),('FILE_SAMPLE','样品'),('FILE_COMMENT','备注')]:
        if m.get(key): rows.append((label,m[key]))
    return rows
