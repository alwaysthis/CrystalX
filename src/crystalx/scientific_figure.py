"""Matplotlib scientific figure renderer shared by screen and all exports."""
import math
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.ticker import Locator,MaxNLocator,LogLocator,LogFormatterMathtext,FixedLocator,FuncFormatter,NullLocator,NullFormatter
from matplotlib.text import Text
from .matlab_literals import parse_literal
from .plot_style import inherited,math_label,tick_text,LINE_STYLES,MARKERS,tick_mode,axis_label
from .plot_scales import axis_scale,apply_scale,RootLocator

class IntervalLocator(Locator):
    def __init__(self,step,logarithmic,square_root=False): self.step=step; self.logarithmic=logarithmic; self.square_root=square_root
    def __call__(self): return self.tick_values(*self.axis.get_view_interval())
    def tick_values(self,low,high):
        if self.logarithmic: low,high=math.log10(low),math.log10(high)
        elif self.square_root: low,high=math.sqrt(max(0,low)),math.sqrt(max(0,high))
        first=math.ceil(low/self.step); count=max(0,math.floor(high/self.step)-first+1)
        if count>10000: raise ValueError('当前范围的刻度超过10000项，请增大间距。')
        return [10**((first+i)*self.step) if self.logarithmic else ((first+i)*self.step)**2 if self.square_root else (first+i)*self.step for i in range(count)]

def make_figure(scan,style,bounds,size,curve_visible=True,name='plot 1',curves=None):
    general=style['general']; width,height=size
    figure=Figure(figsize=(width/96,height/96),dpi=96,facecolor=general['background'])
    figure.set_layout_engine(None)
    padding=8
    position=[padding/width,padding/height,1-2*padding/width,1-2*padding/height]
    data=figure.add_axes(position)
    data.set_facecolor(general['background']); data.xaxis.set_visible(False); data.yaxis.set_visible(False)
    for spine in data.spines.values(): spine.set_visible(False)
    xaxis=style['axes']['bottom'] if style['axes']['bottom']['visible'] else style['axes']['top']
    yaxis=style['axes']['left'] if style['axes']['left']['visible'] else style['axes']['right']
    apply_scale(data,True,xaxis); apply_scale(data,False,yaxis)
    l,r,b,t=bounds; data.set_xlim(l,r); data.set_ylim(b,t)
    legend=style['legend']
    if curves is None:
        from .plot_curves import PlotCurve
        curves=[PlotCurve(scan.x,scan.intensity,style['curve'],legend['text'] or name)]
    artists=[]; handles=[]; point_annotations=[]; thickness_annotations=[]
    for curve_index,item in enumerate(curves):
        curve=item.style; color=inherited(style,curve,'color')
        displayed=item.display_y
        line,=data.plot(item.x,displayed,color=color,linewidth=inherited(style,curve,'width'),
            linestyle=LINE_STYLES[curve['style']],marker=MARKERS[curve['marker']],markersize=curve['marker_size'],
            markerfacecolor=curve['face'],markeredgecolor=curve['edge'],markeredgewidth=inherited(style,curve,'width'),
            label=math_label(item.label),visible=curve_visible and item.visible)
        artists.append(line)
        if line.get_visible() and item.legend_visible: handles.append(line)
        if line.get_visible() and item.fill_baseline:
            baseline=[v-b for v,b in zip(item.fill_baseline,item.background)] if item.subtract_background and item.background else item.fill_baseline
            data.fill_between(item.x,baseline,displayed,color=color,alpha=.13,label='_nolegend_')
        if item.thickness_marks and line.get_visible():
            order=np.argsort(item.x); source_x=np.asarray(item.x)[order]; source_y=np.asarray(displayed)[order]
            for mark in item.thickness_marks:
                x=mark['x']
                if not source_x[0]<=x<=source_x[-1]: continue
                y=float(np.interp(x,source_x,source_y))
                if (xaxis['log'] and x<=0) or (yaxis['log'] and y<=0) or (axis_scale(xaxis)=='sqrt' and x<0) or (axis_scale(yaxis)=='sqrt' and y<0): continue
                data.plot([x],[y],marker='o',markersize=5,markerfacecolor='white',markeredgecolor='#0072b2',zorder=4,label='_nolegend_')
                label=data.annotate(f'{mark["order"]}: {x:.4f}',(x,y),xytext=(0,9),textcoords='offset points',ha='center',
                    color='#0072b2',fontfamily=general['font'],fontsize=max(8,general['size']*.5),annotation_clip=True)
                thickness_annotations.append(label)
        if item.show_background and item.background and line.get_visible():
            baseline=[0]*len(item.x) if item.subtract_background else item.background
            data.plot(item.x,baseline,color=color,linestyle='--',linewidth=inherited(style,curve,'width'),alpha=.6,label='_nolegend_')
        if line.get_visible():
            for candidate in item.peak_analysis.get('fringe_candidates',[]):
                data.plot([candidate['x']],[candidate['y']],marker='D',markersize=5,markerfacecolor='none',markeredgecolor='#b8860b',label='_nolegend_')
            for contour in item.peak_analysis.get('contours',[]):
                xx,yy=contour['x'],contour['y']; base=contour.get('baseline',yy)
                if not item.peak_analysis.get('contour_curves'):
                    data.fill_between(xx,base,yy,color=color,alpha=.13,label='_nolegend_')
                    data.plot(xx,yy,color=color,linestyle='--',linewidth=max(1,inherited(style,curve,'width')),alpha=.85,label='_nolegend_')
            smooth=item.peak_analysis.get('smooth',{})
            if smooth:
                for low,high in smooth.get('ranges',[(min(smooth['x']),max(smooth['x']))]):
                    points=[(x,y) for x,y in zip(smooth['x'],smooth['y']) if low<=x<=high]
                    if points:
                        xx,yy=zip(*points)
                        data.plot(xx,yy,color='#d55e00',linestyle='-',linewidth=max(1.4,inherited(style,curve,'width')),label='_nolegend_')
        for index in item.peaks if line.get_visible() else ():
            x,y=item.peak_position(index)
            if xaxis['log'] and x<=0 or yaxis['log'] and y<=0 or axis_scale(xaxis)=='sqrt' and x<0 or axis_scale(yaxis)=='sqrt' and y<0: continue
            data.plot([x],[y],marker='v',markersize=5,color=color)
            fitted=any(position['index']==index for position in item.peak_analysis.get('positions',[]))
            if fitted:
                top=max([y]+list(displayed[max(0,index-10):index+11])); low,high=data.get_ylim()
                label_y=top*(high/low)**.015 if yaxis['log'] else top+(high-low)*.025
                text_position=(x,label_y); text_coordinates='data'
            else: text_position=(0,10); text_coordinates='offset points'
            annotation=data.annotate(math_label(item.point_labels.get(index,f'{x:.4f}')),(x,y),xytext=text_position,textcoords=text_coordinates,ha='center',
                color=color,fontfamily=general['font'],fontsize=max(8,general['size']*.6),annotation_clip=True,math_fontfamily='stix')
            point_annotations.append((curve_index,index,annotation))
        for index in item.points if line.get_visible() else ():
            x,y=item.x[index],displayed[index]
            if xaxis['log'] and x<=0 or yaxis['log'] and y<=0 or axis_scale(xaxis)=='sqrt' and x<0 or axis_scale(yaxis)=='sqrt' and y<0: continue
            data.plot([x],[y],marker='o',markersize=4,color=color)
            annotation=data.annotate(math_label(item.point_labels.get(index,f'({x:.6g}, {y:.6g})')),(x,y),xytext=(8,8),textcoords='offset points',
                color=general['color'],fontfamily=general['font'],fontsize=general['size'],
                arrowprops={'arrowstyle':'-','color':color,'linewidth':general['width']},annotation_clip=True,math_fontfamily='stix')
            point_annotations.append((curve_index,index,annotation))
    data.curve_artists=artists
    data.point_annotations=point_annotations
    data.thickness_annotations=thickness_annotations
    data.legend_curve_indices=[i for i,line in enumerate(artists) if line.get_visible() and curves[i].legend_visible]
    overlays={}
    grid_sides={'bottom' if style['axes']['bottom']['visible'] else 'top',
                'left' if style['axes']['left']['visible'] else 'right'}
    for side,settings in style['axes'].items():
        if general['box'] and not settings['visible']:
            data.spines[side].set_visible(True); data.spines[side].set_color(general['color']); data.spines[side].set_linewidth(general['width'])
        axis=figure.add_axes(position,facecolor='none'); overlays[side]=axis; axis.patch.set_visible(False)
        horizontal=side in ('bottom','top'); coordinate=axis.xaxis if horizontal else axis.yaxis
        other=axis.yaxis if horizontal else axis.xaxis; other.set_visible(False)
        for spine in axis.spines.values(): spine.set_visible(False)
        if not settings['visible']: coordinate.set_visible(False); continue
        axis.spines[side].set_visible(True); axis.spines[side].set_color(inherited(style,settings,'color')); axis.spines[side].set_linewidth(inherited(style,settings,'width'))
        if horizontal: axis.xaxis.set_ticks_position(side); axis.xaxis.set_label_position(side)
        else: axis.yaxis.set_ticks_position(side); axis.yaxis.set_label_position(side)
        apply_scale(axis,horizontal,settings)
        low,high=(l,r) if horizontal else (b,t)
        if settings['minimum'].strip(): low=float(settings['minimum'])
        if settings['maximum'].strip(): high=float(settings['maximum'])
        if settings['log'] and low<=0:
            positives=[v for v in (scan.x if horizontal else scan.intensity) if v>0]
            low=min(positives)*.9 if positives else 1.
            high=max(high,low*10)
        if axis_scale(settings)=='sqrt': low=max(0,low); high=max(high,low+1e-10)
        if horizontal: axis.set_xlim(low,high)
        else: axis.set_ylim(low,high)
        mode=tick_mode(settings)
        if mode=='array': ticks=parse_literal(settings['ticks']); locator=FixedLocator(ticks)
        elif mode=='spacing':
            step=settings['interval']; start=math.log10(low) if settings['log'] else low; stop=math.log10(high) if settings['log'] else high
            if axis_scale(settings)=='sqrt': start,stop=math.sqrt(low),math.sqrt(high)
            first=math.ceil(start/step); count=max(0,math.floor(stop/step)-first+1)
            if count>10000: raise ValueError('当前范围的刻度超过10000项，请增大间距。')
            locator=IntervalLocator(step,settings['log'],axis_scale(settings)=='sqrt')
        else: locator=LogLocator(base=10,numticks=9) if settings['log'] else RootLocator() if axis_scale(settings)=='sqrt' else MaxNLocator(nbins=6,min_n_ticks=3)
        coordinate.set_major_locator(locator)
        coordinate.set_minor_locator(LogLocator(base=10,subs=tuple(range(2,10)),numticks=1000) if settings['log'] and mode!='array' else NullLocator())
        coordinate.set_minor_formatter(NullFormatter())
        labels=parse_literal(settings['labels'],strings=True)
        if settings['labels'].strip():
            ticks=list(coordinate.get_majorticklocs())
            # Automatic locators may emit ticks beyond the visible limits.
            if mode=='auto': ticks=[v for v in ticks if low-1e-10<=v<=high+1e-10]
            # MATLAB pads missing labels with blanks; additional labels have no tick.
            labels=(labels+['']*len(ticks))[:len(ticks)]
            coordinate.set_major_locator(FixedLocator(ticks)); coordinate.set_ticklabels([math_label(v) for v in labels])
        elif settings['number_format']=='auto' and settings['log']: coordinate.set_major_formatter(LogFormatterMathtext())
        else: coordinate.set_major_formatter(FuncFormatter(lambda value,pos,s=settings:tick_text(value,s)))
        axis.tick_params(axis='x' if horizontal else 'y',direction=settings['direction'],length=settings['tick_length'],
                         width=inherited(style,settings,'width'),colors=inherited(style,settings,'color'),labelsize=inherited(style,settings,'size'))
        axis.tick_params(axis='x' if horizontal else 'y',which='minor',direction=settings['direction'],length=settings['tick_length']*.6,
                         width=inherited(style,settings,'width')*.8,colors=inherited(style,settings,'color'))
        for label in coordinate.get_ticklabels(): label.set_fontfamily(inherited(style,settings,'font')); label.set_math_fontfamily('stix')
        auto=axis_label(scan,side)
        coordinate.set_label_text(math_label(auto if settings['label'] is None else settings['label']),fontfamily=settings['label_font'] or inherited(style,settings,'font'),
            fontsize=settings['label_size'] or inherited(style,settings,'size'),color=settings['label_color'] or inherited(style,settings,'color'),math_fontfamily='stix')
        if general['grid'] and side in grid_sides: axis.grid(True,axis='x' if horizontal else 'y',color=general['color'],alpha=.18,linewidth=general['width'])
    if legend['visible']:
        item=data.legend(handles=handles,loc=legend['location'],frameon=legend['frame'] and bool(handles),prop={'family':inherited(style,legend,'font'),'size':inherited(style,legend,'size')},labelcolor=inherited(style,legend,'color'))
        for text in item.get_texts(): text.set_math_fontfamily('stix')
        if legend['frame']:
            item.get_frame().set_edgecolor(general['color']); item.get_frame().set_linewidth(general['width']); item.get_frame().set_facecolor(general['background'])
    # Reserve only the measured decorations, rather than a fixed percentage.
    for text in figure.findobj(Text): text.set_usetex(False)
    canvas=FigureCanvasAgg(figure); canvas.draw()
    for _ in range(4):
        boxes=[ax.get_tightbbox(canvas.get_renderer()) for ax in overlays.values()]
        boxes=[box for box in boxes if box is not None]
        if not boxes: break
        frame=data.get_window_extent(canvas.get_renderer())
        left=padding+max(0,frame.x0-min(box.x0 for box in boxes))
        right=padding+max(0,max(box.x1 for box in boxes)-frame.x1)
        bottom=padding+max(0,frame.y0-min(box.y0 for box in boxes))
        top=padding+max(0,max(box.y1 for box in boxes)-frame.y1)
        fitted=[left/width,bottom/height,max(.15,1-(left+right)/width),max(.15,1-(bottom+top)/height)]
        if max(abs(a-b) for a,b in zip(position,fitted))<.5/max(width,height): break
        position=fitted
        for ax in [data,*overlays.values()]: ax.set_position(fitted)
        canvas.draw()
    return figure,data,overlays
