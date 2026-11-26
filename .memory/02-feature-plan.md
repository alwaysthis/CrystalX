# 关键功能设计计划

## 0.34.0 膜厚独立标记及崩溃诊断

ThicknessDialog.show_marks在波长来源行右侧，初始无标记时关闭；sync_marks读已勾选的有效x/order，自动模式按x排序编号，手动级次保留。曲线新增thickness_marks list[{x,order}]，独立于points/peaks/peak_analysis；样式replace保持，MIME校验有限x/整数级次并携带，settings/preset排除。scientific_figure按当前display_y在x处插值，蓝色空心圆+级次/峰位注释，data.thickness_annotations保存artist用于核验，隐藏曲线同步隐藏，log/sqrt非正过滤。表格加载后一次同步，编辑/勾选/删除同步，关闭dialog保留；重开从可见标记恢复，非连续手动级次自动切换手动模式。开关关闭只清本组，不动其他标记。

用户报告刚崩溃且忘记操作。只读Windows应用日志确认2026-11-23 01:18:49 pythonw.exe/ucrtbase.dll 0xc0000409，pid0x3018，WER01:18:59；已有crystalx.log只记启动01:14:07，无Python异常，WER临时dump已不可获取，不能认定历史触发点。独立异常回调测试复现prepare(QMessageBox)→install_dialog_chrome引用已删除QGridLayout：Qt在setWindowFlag/setStyleSheet/setSizeGripEnabled后重建原生布局，修复为变更后重新读取dialog.layout。色彩对话框亦回归通过。

runtime.RuntimeDiagnostics于QApplication后安装sys.excepthook/threading.excepthook/Qt消息处理；主回调异常写完整traceback并异步显示主题中文非模态提示，不执行默认未处理abort路径；线程异常写日志。eventFilter只记按钮释放/对话框开关/上下文菜单，无鼠标移动或输入内容。faulthandler打开logs/crash.log保留句柄、进程/时间标识、all_threads，退出恢复hooks并关闭，main日志含PID/Python版本和正常退出。原生致命错误只能记录不能恢复，不宣称已修复历史所有闪退。

101项单元测试（含新独立标记剪贴板），check_xrr_thickness验证表格选中/取消/开关独立及artist数；check_runtime_stability在真实Qt单次回调注入异常，确认有traceback/中文提示且主程序继续，然后三轮主窗口/膜厚编辑与标记/极小尺寸/终端切换/文件信息/背景弹窗/scan切换/tab删除及延迟事件无新异常，并验证faulthandler堆栈文件。100%及150%通过，既有color dialog和全部领域回归通过。测试用临时日志，不污染用户正式日志。

## 0.33.0 XRR条纹膜厚计算

XrdPage在scan.template_name=='XRR'显示thickness_button，图标film_thickness透明SVG，点击ThicknessDialog；其他XRD/RC/AFM隐藏。切换扫描销毁旧计算窗，曲线选择独立，不改变主图曲线/峰/视野。窗口含曲线、轴类型、波长、搜索范围、可选临界角、连续级次checkbox、峰表及结果，原生保存CSV。读取现有峰优先当前PeakFindingDialog同曲线结果连续x，否则curve.peak_position；读取标点用源x。修改后结果失效，q列清空，自动级次不可编辑，手动级次支持漏峰间隔。

xrr_thickness.py Qt无关：estimate_thickness按2theta/2或theta（度）转换qz=4pi sin(theta)/lambda，q_a直接用Å^-1，q_nm除10；可选qc临界角后q'=sqrt(q²-qc²)，要求峰在临界角之上。无显式orders按q排序连续编号，显式orders须整数并随q递增；至少2个峰，禁止重复/非有限。回归q与级次，t_nm=2pi/slope/10，三峰以上用回归斜率标准误传播，intervals_nm含每对级次间隔；两峰无误差统计，R²不作为有效诊断显示。临界角未自动推断，缺波长明确提示CuKα₁1.5406Å备用；metadata支持Angstrom/A/Å和nm换算，实际文件读取1.540593Å。

detect_fringe_maxima在选定正强度范围均匀插值logI，小高斯去噪与宽高斯去包络，find_peaks初始prominence .04，局部高频MAD抑制异方差噪声、前5个候选典型宽度筛过窄伪峰。只提供候选，用户须确认连续同类峰；间距相对离散>15%提示噪声/漏峰/多周期。没有自动宣称单层物理厚度或已排除多层。默认搜索去掉最前10%范围，可改；全部计算不依赖图的log显示或背景扣除，保持源数组。

100项单元测试含已知50nm的θ/2θ/q单位、下降顺序、漏峰与临界角、无效输入/单位元数据、60nm合成衰减条纹。check_xrr_thickness真实按钮、级次编辑/勾选/非法输入/导出/入口隔离，合成自动估计59.9784nm；实际XRR_1在用户可改0.9–2.8°范围候选6个、估计34.3010nm为演示，未确认实物厚度。100%/150%通过，截图output/xrr-thickness-real.png/synthetic.png。Qt布局时画布可能短暂1px，XrdPlot.rebuild在fit_plot前后跳过<32px绘制，避免make_figure负轴区域；后续resize正常重绘。公式依据SasView Kiessig calculator（README链接），原数据只读不入库。

## 0.32.0 原始数据峰型拟合（覆盖0.31仅平滑轮廓的默认模式）

用户宽峰截图说明7点SG仍跟噪声并在22.13/22.21/22.24等位置误标多峰。新增Qt无关peak_fit.py，不修改原强度；PeakSettings.method加fit，domain默认prominence兼容原API，UI默认fit推荐。fit_model默认split_pv（左右全宽不同），另有pseudo_voigt/gaussian/lorentzian。profile用峰高h[(1-eta)exp(-4ln2*u²)+eta/(1+4u²)]，eta为洛伦兹比例；左右宽度按中心分段，FWHM=(left+right)/2，非Mantid归一化面积参数化。README链接SciPy least_squares与Mantid原文。

种子信号仅用1.5采样点高斯预处理定位，保留prominence>=max(阈值,相对高度10%)、种子宽>=max(用户最小,4采样步)以抑制噪声/欠采样极值。支持区间约±4种子宽及最小6步，按区间左端排序合并重叠组，组内中心排序，最多40候选/每组8峰，过多提示框选/阈值。对原始观测联合拟合分峰+线性基底，x/y归一化、有边界least_squares soft_l1/x_scale=jac，最多600评估。中低动态范围噪声缩放残差，强动态>=1000用sqrt(count/noise²)权重；近候选尝试减分峰，仅BIC改善才接受。R²<.65组不显示，未收敛提示。模型拟合不是普适物相/物理模型判断，无不确定度估计。

Peak附加r2/fitted_y；x为连续模型中心，index仍为最近源采样点，source intensity列不改。fit模式表格/CSV列为拟合峰高、局部R²及FWHM；其他模式原半突出度宽度不变。PeakResult.overlays的smooth存每组400–1600密集模型点（总最多64000），contours为分峰+基底，positions存源index/连续x/总模型y。PlotCurve.peak_position统一峰标记与默认图注，clipboard校验有限值/索引及密集轮廓上限；settings不带分析数据。scientific_figure橙色改连续实线，模型轮廓与图像导出共用；标记不再落在噪声最高源点；拟合标签上移至邻近原始噪声上沿，避免文字与峰顶噪声重叠。

PeakFindingDialog切fit时禁用/取消SG平滑，显示控件名改“显示峰拟合曲线”（默认打开），切非fit仍显示检测平滑；复制/样式/扫描保留分析，clear和扣底信号改变仍使旧分析失效。模型不可靠给出扩大范围/调整阈值建议，峰型/检测参数需开始寻峰提交。

95项单元测试含噪声宽不对称峰单峰/中心/FWHM、四种理想模型、真实可分辨双峰、下降ROI源索引/密集模型剪贴板及非法输入。check_peak_fit_ui覆盖真实默认拟合、模型峰位artist/显示开关不重拟合、FWHM/R²/CSV、样式/复制/导出；100%及150%通过。实际BTO-13-B/rc_44.4378.ras为单主峰，中心22.21331974°、FWHM .34769729°、R² .98464419。实际BTO XRD也检出6候选（阈值118.19136），原文件只读。output/peak-fit-real.png和peak-fit-dialog-real.png已人工核对，原黑线不变，拟合橙线连续且仅一个主峰标记。

## 0.31.1 公式下拉选中态与继承色块

原MathItemDelegate使用系统HighlightedText（白）叠在QComboBox实际浅色选中背景上，且原生focus框变成黑色圆角行框。MathComboBox单独使用MathComboDelegate，普通文字/公式统一白底、选中#dce7df/字#23482f、hover#edf3ef，不绘制原生行内focus框；图标/checkbox保留。其他列表/表格委托不变，FontChoice仍使用自己的CompactRows。popup view明确浅色边框与outline=0，源码/当前值及选择回调不变。

PlotColorButton不再使用QSS dashed rounded border：QPainter抗锯齿1px、1.5px内缩、4px半径，四个完整对称圆弧+每条直边镜像等距虚线，自定义色同尺寸填充，透明为斜线区别继承空框，hover/focus只改边框色不增粗。禁用降低opacity，不使用窗口遮罩。set_color仍发原colorChanged，虚线几何由绘制实现，检查不再搜QSS字符串。

check_plot_control_rendering实际打开两条曲线公式下拉，选中行像素深色文字/浅绿底断言，色块左右镜像误差核验；100%、150%、200%通过，截图output/formula-popup-{1,1.5,2}.png及color-swatches-{1,1.5,2}.png已人工核对。check_background_controls/check_math_and_multiopen/check_plot_curves回归。

## 0.31.0 强峰背景修订、多种寻峰与分析叠加

本节覆盖0.30默认线性AsLS的决定。实际BTO-13_10-110_1.ras在百万计数强峰下，旧背景−5.603871–18.394395、46.47°处18.21019，明显被峰拉高且自然边界有负值。默认auto按ptp/max(median(abs(y)),ptp*1e-9,eps)>=1000选择snip，否则asls，温和斜底保持原精度。SNIP均匀网格最多20000，计数先移动平均（默认x跨度1%全宽），LLS=log1p(log1p(sqrt(counts+1)))、reflect补边、默认半窗跨度2.5%、从大到小递减削峰，再逆变换；非负计数的模型背景约束>=0，不裁切原始或扣底后的数据。新实际背景0.381416–1.065917，46.47°处0.491473。纯SNIP对斜底仍有近似偏差，不能因此声称普适精确。

background.py METHODS auto/snip/median/asls；median先分块均值减计数噪声，宽窗口中位数+高斯平滑，默认全跨度20%。BackgroundDialog由工具栏背景开关右侧无框三点进入，可选曲线/方法/窗口/预平滑，apply显式重算。字段名window_width，不覆盖QWidget.width()。PlotCurve.background_settings随曲线/复制保留，settings/preset不带；外部字段类型/键和值校验。set_background返回当前强度是否改变：仅隐藏背景不清分析，扣底开关变化或已扣底时重算背景才清峰/叠加及旧寻峰表。

PeakSettings新增method(prominence/derivative/wavelet)、wavelet_min/max（横轴尺度非FWHM）。突出度find_peaks；derivative在均匀x网格高斯平滑sigma=max(.5,window/6)后计算实际x梯度正→负过零，映回近邻峰；CWT用SciPy find_peaks_cwt（最多32个对数间隔尺度，默认2..min(50,n/20)采样点、min_snr=2），在均匀x检测后映射到原数据局部峰。共享突出度/间距/半突出度宽度筛选及FWHM，ROI与下降源索引保持。依据SciPy官方find_peaks_cwt和pybaselines官方SNIP/LLS文档，README链接原文；无新依赖。

PeakResult.overlays缓存contours（检测信号/端点局部基底的XY）与smooth（实际检测信号，另存每峰ranges）；contour范围取prominence bases与±3FWHM的交集，非峰型拟合。对话框三个独立显示开关，show_smooth在未平滑时启用SG并重跑，关闭SG亦关闭平滑显示。PlotCurve.peak_analysis持有可见叠加，scientific_figure统一绘制淡填充/虚线轮廓、橙色点划线平滑峰，只画峰邻域，不进入图例；export保留，clipboard校验/携带，settings/preset排除。clear_marks清峰及分析但保留手工点；改变参数需开始寻峰提交结果。

90项单元测试，包括三法高斯定位/FWHM、ROI/下降/平滑源索引、百万峰背景抗污染、分析剪贴板/非法输入。check_peak_methods_ui覆盖真实下拉/三开关/显示平滑自动重跑、样式保存与图例隔离、背景设置/扣底失效/隐藏不清、复制/透明导出，100%与150%通过。实际RAS突出度200时三法候选数6/6/5，非自动阈值对比，不代表物相判断；新背景范围已验证非负且<2。check_strong_peak_background生成output/xrd-background-comparison.png，另有peak-methods-real.png/peak-overlays-real.png；只读研究文件，不复制原数据入仓库。

## 0.30.0 25pt模板、直接色块、FWHM及背景处理

default/plot.json与default/plot-templates五模板general.size=25，显式轴/图例size或label_size也统一25，0继承保留；按用户“每个模板”要求仅修改本机custom/plot-templates/XRD.json字号，其余设置保留，custom不纳入Git。PlotColorButton直接选色，继承''/auto为灰色虚线28px空块，右键恢复默认、marker可none透明；无mode/custom下拉。FontChoice继承值''空项、数值继承0显示空白，序列化哨兵不变。旧检查已改用set_color，不保留虚假的旧模式控件。

Peak新增fwhm独立于width。half_maximum_width用SciPy prominence左右bases构建局部线性基底，扣底后从峰向两侧找半高包围点，在实际x插值，返回全宽；截断/不可靠交点None。不是把原半突出度宽度换名字，也不是非线性峰型拟合；重叠峰有局限。PeakFindingDialog六列含FWHM、CSV五数据列，原始强度字段仍从curve.y源索引读取；检测/ROI使用display_y，平滑仅影响检测信号。依据SciPy官方peak_widths（半突出度非FWHM）和Eilers/Boelens 2005 AsLS文章（README有原文链接）。

background.fit_background独立Qt，严格单调/有限XY，下降映回原序；均匀x插值最多3000点，二阶差分惩罚AsLS，lambda=1e6*(n/1000)^4、p=.001、最多30次稀疏求解，最后映回原采样；背景估计不承诺物理模型，端点自然边界可有偏差。PlotCurve保存background/show_background/subtract_background，display_y派生原y减背景，不改原数组。scientific_figure/selection/hover/标点/重置范围/峰检测统一display_y；背景虚线不进图例，扣底时参考线为0，对数mask非正数。apply_style改dataclasses.replace保留处理状态，clipboard含背景并校验形状/数值/布尔，settings/preset不含背景。

XrdPage居中工具栏两checkbox，XRD类含XRR/RC显示，AFM/XY不显示；各曲线分别缓存，当前选择否则首条，selection_changed同步且blockSignals避免重入。show/subtract独立，subtract可直接计算背景。切换处理清旧峰标记与已开寻峰结果，保留手工点和原数据，重算显示范围。切换扫描恢复状态，复制保留处理和数据，粘贴样式仍继承目标。

85项单元测试含高斯FWHM、倾斜底、非等距/下降、无效输入、常值底与背景剪贴板；check_background_controls真实开关、图线数组/源数据、样式保留/直接取色/空框、FWHM CSV、扫描隔离、逐曲线切换及导出，截图direct-plot-colors.png/background-corrected.png。背景估计误差容许自然端点偏差，不将平滑基底声明精确物理背景。已有曲线/论文/峰/视野和模板检查通过。

## 0.29.2 单行公式预览与取消曲线选择

QTextDocument.adjustSize默认会给长文字计算折行宽度，随后draw_text按控件高度缩放整段，导致截图里的图例名称/当前曲线文字变成两行小字。document在width=None时设置QTextOption.NoWrap，指定width的wordWrap标签保持可换行；MathLineEdit和MathComboBox非编辑态预览将源码换行视觉转为空格，按单行裁切，不修改原字符串。check_math_and_multiopen增加O2/800℃长混合文字lineCount==1及原文不变，截图已核对。

XrdPlot单击图内空白select_curve(None)，键盘Esc同样取消并清hover/readout；手动框选模式Esc仍优先cancel_peak_selection。拖动平移不取消，单击曲线继续标点；双击空白原重置视图不变。check_curve_selection_style真实鼠标点击和Esc断言选择清空、bounds及曲线样式不变。

## 0.29.1 曲线选择不遮挡实际样式

截图中第二条曲线的黄橙色来自CurveSelection连续2.5px橙色覆盖，并非Matplotlib未更新：apply_style及legend_handles使用相同真实颜色。改为可见范围内最多12个5px半径无填充灰绿空心圈，近点去重，不再重画整条线，颜色/线宽/线型可直接检查，选择仍不进入导出。图例色线随曲线，图例文字由legend.color或general.color独立控制，默认黑色，未擅自改为曲线色。

check_curve_selection_style实际新增并选中第二曲线，通过样式弹窗红→紫→绿重复应用、线宽、首曲线隔离、legend_handles颜色、屏幕源点附近实际颜色像素、选择不入透明导出及隐藏/恢复；截图output/selected-curve-style.png。新增数据后原bounds保持不变，测试主动reset纳入新数据，以免把范围外曲线误判为颜色缺失。

## 0.29.0 显式数学语法、目标图继承与多选打开

本节覆盖旧版0.28的无$自动识别规则，以及早期曲线复制时物化源颜色/线宽的决定。math_syntax统一仅匹配完整`$...$`/`$$...$$`，math_label不再隐式包装反斜杠或上下标。Mathtext数学子集，非任意LaTeX宏包引擎。math_ui共享MathLabel/LineEdit/ItemDelegate/HeaderView/Table/Tree/List/Combo/Push/Tool/Check/PlainTextEdit/Menu，组件无公式时走原Qt绘制；焦点编辑源码，失焦预览，未完成/非法公式显示原文。formula_image LRU256透明PNG，按DPI渲染，QTextDocument混排；自绘工作区tab、原子标签、曲线hover亦复用。原生文件选择器/颜色对话框内部Qt类不替换，dialog_chrome使用QtPushButton识别原生按钮。HelpButton有text类属性，MathToolButton必须用基类QToolButton.text(self)，避免Qt回调异常退出。

PlotCurve.clipboard不再物化源图通用值，paste_curve调用inherit_plot_appearance将color=''、width=0、非none的face/edge='auto'，保留数据、图例名、线型/marker/size、标点/峰/图注。目标通用颜色/宽度更新曲线与legend，源对象不变，目标bounds不变；之后可在目标曲线页独立编辑。

MainWindow.open_file原生getOpenFileNames→load_paths；load_path(report_errors=False)收集失败并在批量结束汇总，不阻断后续成功文件。混合结构/XRD/AFM独立tab，SessionState记录最后成功路径。添加曲线亦多选，全部扫描依次加入；取消/失败不更新目录。80项单元测试及check_math_and_multiopen、check_ui、check_visibility_editing等交互检查；数学预览截图output/math-widgets-dollar-rule.png，源码不改写，源文件不入库。

## 0.28.0 居中分析、手动范围与文件信息
PlotHeader独立排布左文件按钮/中央分析/右图片工具，分析中心不受两侧宽度影响；空间不足转两行，仍居中且不重叠。顶部手动寻峰/自动寻峰/三点：自动run=True在显示前执行整曲线；手动start_peak_selection进入矩形模式，左键拖动，松开将像素框经transData反变换成原始XY区间并运行，同一PeakFindingDialog显示结果。Esc取消；框选中不平移/标点，滚轮冻结；绿色半透明矩形在Qt overlay内，不进入导出。反变换适用于log/sqrt。边界少于3点提示，框选需含两侧背景。
detect_peaks增加region，先按X区间保留索引，再处理降序、检测及原始Y范围过滤；Peak.index始终指完整源曲线。窗口显示范围，scope变化清旧结果，自动恢复全曲线；三点只打开现有窗口不自动运行，保留参数/标记开关及结果，曲线名刷新。手动结果替换该曲线自动标记，手工点独立保留。切换扫描关闭寻峰窗。
math_label增加无$上下标识别，如I_{001}/x^2，仍为Mathtext LaTeX子集。PlotCurve.point_labels字典存源索引自定义图注，手工点和寻峰标记均可双击文字进入PointLabelEditor，验证/试绘后提交；data.point_annotations保存artist到源点映射。apply_style/复制/扫描保留，preset不含；剪贴板校验索引和公式，旧payload兼容。清手工点只移除相关图注，不误清自动峰专属文字。
主界面selector隐藏兼容现有代码，文件信息FileInfoDialog内选择扫描、读取当前模型元信息，不重读研究文件。scan_info Qt无关：XRD/XRR/RC展示点数/范围/步长/扫描模式与时间/速度/仪器/靶材/波长等已有字段；AFM标题AFM高度，按y像素频数加权mean、population variance/std、众数高度、最高频数、weighted median、有效高度范围、Ra、总像素，统计为分箱估计而非二维原始形貌计算；全零频数给出不可统计说明。
78项单元测试含ROI源索引/降序/XY筛选、加权统计/零频、图注复制/无$上下标；check_peak_workflows真实点击自动、三点、ROI拖拽/Esc、标记开关、图例/手工/自动峰LaTeX双击、文件信息扫描切换、宽窄居中不重叠。实际AFM均值0.048565654nm、方差0.461227132nm²、std0.679137049nm、众数-0.1088nm；原文件不入库。既有XRD/AFM/图例/论文检查通过。

## 0.27.0 XRD寻峰工具栏与候选结果
XrdPage顶部分析工具栏含寻峰图标+文字，仅data_kind=XRD（含XRD/XRR/Rocking Curve）显示，AFM/XY不显示。PeakFindingDialog中文主题窗，曲线选择、突出度0自动、物理x单位最小间距/最小最大宽度、可选SG和平滑奇数窗口，候选结果表、显示峰位、清除自动标记、CSV导出。切换扫描关闭窗口，曲线切换清空旧结果。独立分析不受图的log/sqrt显示影响。
新增SciPy>=1.15,<2（本机1.18.1已安装），首次打开寻峰才导入。peak_finding独立Qt无关领域层，finite/单调x校验，降序反转并映回源索引；find_peaks以prominence与width=(None,None)、rel_height=.5检测。以插值左右交点转换真实x宽度，按突出度降序在物理x距离抑制邻峰，再按x输出；不是简单将角度除步长，支持非等距数据。SG可选二阶、默认关，仅均匀x允许，原始y不改；表强度仍为原始采样值。
自动门槛=max(5×差分MAD噪声估计,信号范围0.01%,float epsilon)，属于本项目默认启发式，弱峰可手动降低。默认间距5×平均步长、最小宽度2×平均步长；最大宽度0不限。不是物理物相鉴定或精修。峰位为采样点，宽度为半突出度宽度（背景不平/重叠时不是FWHM），精确峰位/FWHM可后续用局部pseudo-Voigt等拟合。
PlotCurve新增peaks源索引，与手工points分开；render用三角标记和峰位文字，显隐随曲线，不进入图例。apply_style保留peaks，剪贴板兼容缺省空并校验索引；settings/presets不含峰数据。寻峰不改POSCAR/研究原始数据。
74项单元测试覆盖Gaussian位置/宽度、噪声/平峰、物理距离/非等距、降序索引、SG/无效输入及复制。check_peak_finding覆盖真实点击入口、结果/原数据和bounds不变、显隐清除与手工标点隔离、样式保留/CSV/无效窗口。实际BTO-13_10-110_1.ras自动阈值118.1913625检出6个候选峰：21.68、22.74、44.18、46.47、72.55、104.14°；最强46.47°。保留ignored截图，原文件不入库。
依据SciPy官方find_peaks、peak_prominences、peak_widths、savgol_filter文档，CWT可作为后续多尺度方案，本轮未实现CWT或峰型拟合；不要把检测宽度宣称为拟合半高宽。

## 0.26.0 AFM单位头XY文本与高度分布
用户指定外部AFM/20261121/Height/BTO-13-A_261121_Z Height_Forward_003_Region.txt，只读核对实际为X Unit: NanoMeter、Y Unit: Pixel及X/Y两列，128点、原X降序、高度-2.3489到10.0205 nm、频数合计65536，最大5161对应-0.1088 nm。这是高度频率曲线，没有二维空间坐标，不能当作AFM形貌矩阵重建。
curve_data.XYScan提取共用Qt无关模型，保留intensity字段供已有消费端兼容，xrd_io.XrdScan为别名。metadata提供DATA_KIND/PLOT_X_LABEL/PLOT_Y_LABEL；y_label集中默认Intensity及覆盖，RAS逻辑/旧两列语义保持。afm_io按单位头识别，不靠文件名；长度单位+Pixel视为AFM高度分布，标准单位缩写Height(nm/µm等)、Pixel count，其他单位头文本为XY并显示X(unit)/Y(unit)、global模板。解析校验完整/重复/乱序单位头、两列有限值、至少两点及非负频数；负高度合法。保留顺序、零值和原单位元数据，不归一化/平滑/重分箱。
read_plot_data为兼容read_xrd的中性入口，MainWindow文本数据经内容分流，共用XrdPage/Plot而非复制绘图库。标题/状态/打开消息区分AFM/XY/XRD，选择器在AFM显示曲线；hover读数用真实y_label。新增default/plot-templates/AFM.json：20pt Times黑色图框、线性，自适应，防止误套XRR对数/2θ/Intensity。既有样式/多曲线/图例编辑/标注/范围和导出/成功目录记忆复用。
新增4项test_afm，69项单元测试通过。check_afm可传外部实际文件，只读验证128点、单位、模型保持、样式标签、hover/zoom、透明PNG、SVG/PDF、失败不更新目录、结构/AFM切换及关闭。实际文件检查成功，截图output/afm-distribution-screen.png与transparent.png，研究原数据不复制入仓库；check_xrd和check_publication_plot回归核验。

## 0.25.3 经典对数主次刻度
此前scientific_figure对所有轴强制NullLocator次刻度，导致log虽然坐标变换正确却缺少数量级内部疏密刻线。对log且非显式数组模式添加LogLocator(base=10,subs=2..9,numticks=1000)和NullFormatter，次刻度长为主刻度0.6、宽为0.8，方向/颜色共用设置。主刻度/标签格式不变，数组模式（含[]清空）保留精确自定义，不额外插入次刻度。四轴以及共享Figure的屏幕、PNG/SVG/PDF同时生效，缩放后Locator动态重算。
新增测试核验四轴每个数量级2..9、20..90的刻度位置，投影间距递减，短刻线及无次标签；显式空数组和线性轴无次刻度。65项测试、check_publication_plot及classic-log-ticks.png截图核验通过。测试自带模板预期改为直接读取default模板，不受用户已保存custom覆盖影响。

## 0.25.2 刻度页、上标科学计数及统一勾选框
scale选择从轴线页移到第二个刻度页顶部；number_format新增scientific，tick_text返回Mathtext的mantissa×10^{exponent}（美元分隔）供原FuncFormatter渲染，数字precision控制尾数小数位，0独立显示0。验证允许新枚举，保留E/e/fixed/auto和自定义标签优先规则。测试验证实际glyph没有^字符、指数小字号且基线上移，不把字符串存储的Mathtext源码误当成显示结果。
theme.CHECKBOX_STYLE同时加入CONTROLS和MENU_STYLE，QCheckBox/QAbstractItemView/QMenu indicator统一16px、1px暗绿边框及2.4px深色SVG勾，partial同步16px；CenteredCheckDelegate用共享尺寸+边框空间居中，避免裁切。刻度子菜单移除各项icon，使用QActionGroup排他勾选，防止图标占据勾选列；根菜单图标仍保留。可见性QMenu QAction应用同一indicator样式。
PlotTextEditor QLabel透明，使标签内容/图例内容一行显示DIALOG_BG；输入框仍白色。图内空白菜单顺序重置、粘贴、添加曲线、图片样式、复制图片、导出图片。
63项单元测试；check_plot_menu_style覆盖分页归属、科学格式、当前唯一勾选、弹窗说明行像素、菜单顺序并保存截图，100%/150%通过；check_visibility_editing检查结构混合勾选/表格编辑，图例及轴交互也通过。

## 0.25.1 双击编辑图例内容
scientific_figure将实际可见图例条目对应源曲线索引存data.legend_curve_indices，legend_entry_at按Matplotlib文字bbox和DPI比例命中，不按名称查找，兼容同名与隐藏曲线。左键双击文字先清除legend_drag再打开LegendLabelEditor；拖动仍独立生效。PlotTextEditor共用主题化中文编辑UI，AxisLabelEditor/LegendLabelEditor只提供保存回调。
set_legend_label先用apply_style校验/试绘再提交，保留bounds/legend_anchor，并同步已打开且有对应行的曲线样式草稿、当前字段和下拉名称；未确认不修改，数学错误内联。切换扫描关闭旧图例编辑器。check_legend_editing核验真实双击、同名/隐藏索引、取消/非法公式、Enter、草稿同步、位置/视野不变、复制带新名与扫描切换，原check_plot_interactions复跑覆盖轴编辑及图例拖动。

## 0.25.0 轴范围、图片比例与模板应用
axis interaction新增interaction_axis，图框上/右装饰边映射到实际可见下/左轴。轴上滚轮沿对应坐标的变换空间围绕指针缩放，只更新对应轴范围；图内滚轮仍双轴缩放。set_axis_range先校验和试绘再提交，主轴更新对应bounds切片，独立副轴只改自身限值；样式草稿的范围保持当前图状态，不能被旧草稿覆盖。move_bounds在平移/缩放后同步已有显式范围，避免主数据轴移动而刻度轴冻结。
右键范围为QMenu+QWidgetAction承载AxisRangeControls，最小/最大输入默认当前有效值，留空为自动，支持Enter或应用，验证错误内联且不提交；成功关闭菜单。样式轴线页移除minimum/maximum字段，write_plot_config不导出轴范围，模板不携带当前视野。
general.aspect='auto'默认，支持4:3/1:1/16:9及可编辑宽:高或数值，aspect_ratio统一验证有限正值及0.1–10比值。PlotAspectHost居中适配完整XrdPlot几何，画布事件仍为本地坐标无需逐项偏移；导出直接使用相同比例Figure。宿主背景QSS按objectName限定，避免污染弹出菜单。支持窗口缩放和恢复自适应；比例变化保持数据bounds。
四个default/plot-templates及default/plot.json统一box=true、size=20、Times New Roman、black、aspect=auto，XRR原log保留。底部确定/应用于模板/应用/取消；应用仅当前图，应用于模板先应用并原子保存当前模板，不广播已打开图。PlotTemplates.writable_path将内置模板映射至custom/plot-templates同名，外选用户模板写回原文件；自带模板保持只读。选择/加载草稿不写文件。
form标题行用DIALOG_BG背景，白色仅内容；坐标轴补标题且选择框位于标题行右侧。check_plot_ranges_aspect覆盖三种刻度实际轴滚轮、上边框映射、真实范围子菜单、非法输入、样式无范围、比例及导出尺寸、模板custom覆盖及自带文件字节不变。62项单元测试、曲线/交互/论文/工作区检查通过并人工核对标题行、比例、范围截图。

## 0.24.0 标签回归样式、论文预设色与根号轴
坐标轴标签文字重新加入样式窗口轴标签页，None显示有效自动标签，清空为显式隐藏；保留双击编辑，set_axis_label同步已打开草稿字段。模板仍按0.23规则不覆盖图内容、导出样式不携带轴文字；加载时保留当前输入（包含尚未应用的文字）。
config/default/plot-colors.json集中48色（灰阶与常用科研多曲线配色），QColorDialog.create通过Qt的setStandardColor替换标准色，不触碰用户custom色。中文标题预设颜色，原取色/Enter/透明绘制保持。Qt PyQt6有standardColor/setStandardColor但无standardColorCount，固定48个标准色槽并测试所有槽。
轴右键菜单改为刻度子菜单，悬停由QMenu原生展开，线性/根号/对数三个勾选项及图标。样式轴线与范围同样用三选一下拉。存储保留旧log bool并加sqrt bool，校验互斥，缺少sqrt的旧预设补False。
plot_scales.py封装RootScale/RootTransform/RootLocator，sqrt变换负值mask，逆变换平方；主数据轴和独立四轴一致使用，刻度标签显示原始数值，默认tick在sqrt空间等距。IntervalLocator根号间距按sqrt值，数组优先仍为数据原值；根号限制输入范围/刻度>=0。reset_bounds和move_bounds在sqrt空间留边和缩放，平移不穿过0；导出共用Figure不修改原数据。旧log及XRR模板行为保持。
新增3项根号领域测试，61项单元测试通过；check_plot_interactions用真实鼠标悬停等450ms验证子菜单展开及切换、根号缩放；check_publication_plot通过样式文字字段编辑数学标签，check_color_dialog校验48色与原交互，check_plot_curves核验菜单结构。

## 0.23.0 图交互、标签内容和文件模板
只读参考x_rheed studio的DragLegend：受绘图范围约束的自由拖动及移动光标。本项目沿用Matplotlib图例以保留科研导出，左键图例时不平移数据；用轴归一化坐标legend_anchor记录左下位置，rebuild/apply/resize后重设set_loc，修改预设位置时清除anchor。每扫描保存style/template/path/anchor/曲线，切换互不污染。XrdPage把PlotToolbar重新放入图外顶部行右侧，工具栏不再覆盖曲线或导出。
CurveSelection增加hover_point响应圈和坐标气泡，只在Qt叠层绘制；近曲线移动更新最近点，离开清除，单击（位移<4px）标注，拖动仍平移。右键曲线沿用选择+菜单。双击轴标签通过实际Matplotlib文字bbox命中打开AxisLabelEditor主题化中文窗，验证数学式后应用；图片样式移除label内容字段，保留label_font/size/color。标签变化同步打开样式草稿，模板加载保留当前内容，write_plot_config清除轴标签文字为None。
PlotTemplates读取config/custom/plot-templates优先于default同名文件，损坏配置记警告并回退；四个内置模板global/XRD/XRR/Rocking Curve，XRR左轴log=true。XrdScan.template_name优先显式测量类型/注释，Omega→Rocking Curve，耦合扫描非负且最大角<=10→XRR，否则XRD，未知global；这不是无歧义物理分类，用户可选择模板修正。Omega显示ω。该目录实际RAS头部没有强制实验类型标识，XRD/XRR都是TwoThetaOmega，已记录范围推断的局限。
样式左导航下方选择模板按钮+当前应用模板，待应用另标，应用才写入plot模板身份；移除设为默认按钮，原加载/导出仍在左下。选择任意JSON文件支持自定义模板，修改不自动写回文件。默认模板含完整样式，不带研究数据。
check_plot_interactions实际鼠标核验图例、轴文字双击/Enter、悬停透明导出、单击标点、右键选择、工具栏在图外、模板草稿/内容隔离/逐扫描恢复。只读检查用户20261121目录14个RAS：XRD4、XRR2、Rocking Curve8均识别匹配目录；58项单元测试及曲线/论文样式/工作区检查通过。

## 0.22.1 XRD真实右键事件修复
2026-11-22用户报告右键闪退，实际发送QContextMenuEvent复现TypeError：event.pos()为QPoint，curve_hit中的QRectF.contains要求QPointF；此前测试直接传QPointF漏检。Windows记录15:21:59 pythonw/Qt6Core 0xc0000409退出，与Qt回调未处理异常退出一致。context_menu入口统一QPointF，contextMenuEvent显式accept并finally deleteLater菜单。check_plot_curves新增Canvas实际上下文事件分发、定时关闭嵌套菜单循环、异常钩子断言，覆盖空白/曲线/轴三种位置。

参考项目：E:/我的文件/personal-lib/lattice，只读参考，不修改。已阅读 README.md 和 crystal.m 头部。

## 当前实现
已接入 VASP 5 POSCAR/CONTCAR/.vasp 读写，正缩放及负目标体积、Direct/Cartesian、Selective dynamics 和标签保留；原子/晶胞真实投影显示，元素与原子/表格选择，分数或笛卡尔平移，命令式撤销/重做，未保存提示及原子替换保存。科学领域模块不依赖 Qt。

不支持 VASP 4 无元素名称、三缩放因子、速度和其他尾部区段；遇到这些输入明确报错。已接入笛卡尔轴旋转（几何中心/原点）、对角超胞、复制/删除、所选 wrap、T/F 标志修改；这些操作使用精确快照命令撤销。当前无化学键、周期镜像、CIF、镜像/真空/薄膜等功能。

超胞 UI 倍数为 1–20，轻量视口最多生成 10000 原子。复制采用当前坐标系的平移量；删除全部原子禁止。改变数量和撤销/重做后清空选择，避免旧编号指向其他原子。QPainter 为轻量投影视口，后续按需求评估渲染后端。

## 计划
1. 独立结构模型：晶格、元素、分数坐标、选择状态、自定义标签和 Selective dynamics 标志。
2. POSCAR/CONTCAR/.vasp 读写：明确缩放、元素顺序、Direct/Cartesian 和选择性弛豫语义，建立往返测试。
3. 三维可视化：原子、晶胞、键、拾取、相机及周期显示；渲染库待评估。
4. 编辑：选择、平移、复制、删除、旋转、镜像、反演、元素替换、wrap、超胞、真空层及薄膜；逐项核对 MATLAB 语义。
5. 撤销/重做、未保存提示、导出确认。
6. VASP 输入集生成：先 POSCAR；INCAR/KPOINTS 后续讨论，POTCAR 由用户提供授权本地来源。

## 已确认界面方向
用户已选择概念图 C：极简浅色，暖白与浅灰底色、低饱和绿色强调，左侧导航、中间大视口、右侧属性。坐标表按需展开。

## 兼容边界
旧 MATLAB 实现不支持 CIF 和速度区段；Python 首版范围待确认，不默认为已有能力。

## 2026-11-02 布局修订（用户明确要求）
左栏使用晶格参数/原子列表选项卡；原子列表按编号、元素、标签显示，右侧按钮展开 Cartesian 与 Direct 两行坐标。标签栏右侧三点菜单打开非模态坐标窗口；两个参考系用标签切换同一张表，保留滚动与选择，结构编辑实时同步。右栏仅放操作。视口顶部提供正交视角、适合窗口，左上角内置竖排选择/旋转/平移/缩放图标工具。底部独立交互消息区可清空。

## 2026-11-02 交互修订（覆盖之前布局）
左侧合并为连续晶格参数及原子列表，不使用选项卡。视口顶部平铺 a/b/c、a*/b*/c*、等轴测图标，按真实直接/倒易基矢方向观察；缩放至结构保持视角。默认箭头工具为旋转，第二工具为叠加点选/框选；任意工具双击拾取叠加，顶部取消全部选择。去掉画布引导文字；基矢为深度排序着色箭杆及锥形头的立体投影。元素色表使用 OVITO 官方 VESTA 主题（config/default/VESTA.ovito-theme），未知元素灰色。

## 2026-11-02 最新选择和布局规则
列表行仅用于查看信息，不改变结构选择；倒数第二列选择按钮才选择原子，最后一列直接展开/收起坐标。默认选择替换，Ctrl 叠加，单击画布清空（选择工具点击原子仍用于选择）；移除顶部清空按钮。双击选择在所有工具下可用，单击清空延迟至双击判定结束，避免干扰 Ctrl 双击。侧栏数值三位小数、双坐标表列对齐，弹窗保留九位；列表紧凑、分区加粗标题和分隔线。视角图标仅字母并居中，竖排工具顶齐。

## 0.8.0 界面与显示规则（覆盖旧说明）
窗口与应用标题 CrystalX，文件菜单收纳打开/保存/导出/退出，标题后为图标撤销/重做。最后一个视角按钮重置方向、缩放和平移，与视角按钮紧邻。界面背景更浅、图标使用高分辨率 SVG 渲染，列表选择按钮使用原子定位图标。底部移除清空按钮。左栏晶格参数右侧显示实空间与倒空间晶胞及立体箭头；倒易基矢采用不含 2π 约定，两图分别归一化。原子视口自动映射分数坐标至晶胞，并复制边界镜像以补齐闭合晶胞；镜像拾取映射回源原子，选择高亮同步；显示不更改模型或导出坐标。

## 0.9.0 标题栏与紧凑图标
最上方改为自定义标题栏：CrystalX 后紧邻撤销/重做，右侧窗口控制；标题栏拖动调用系统移动，双击最大化/还原，右下角可拖动缩放窗口。文件菜单位于其下。移除侧栏分区分割线，缩小视角及工具图标。

## GitHub 发布
用户指定仓库 https://github.com/alwaysthis/CrystalX.git，首次发布采用 main 分支，README 整理为对外说明；虚拟环境、日志、用户配置和临时输出不入库。

## 2026-11-14 工作台修订
参照 zaxoniu/x_rheed studio 的 theme/constants.py 浅色紧凑控件与滚动条设计。统一 hover/pressed；WheelGuard 屏蔽数值框与下拉框滚轮改值。标题菜单栏合并为 app 图标/撤销/重做/文件。assets 下有 SVG 与多尺寸 ICO；create_shortcut.vbs 可在任意 checkout 生成无终端启动快捷方式；.lnk 含绝对路径不提交。Windows 设置 AppUserModelID，窗口图标用于任务栏。
Gemmi 解析 CIF 并展开对称性；部分占位/混合重合位点明确拒绝，CIF 保存引导导出 POSCAR，不覆盖源 CIF。
原子半径使用 VESTA 主题 display_radius（显示比例 0.42），增加高光、按深度渐变透明；选中为统一黄色圆和贯穿十字。透视菜单强度 0–100，默认 0 正交，缩放及拾取跟随透视。左预览可旋转，晶胞右侧独立光泽方向轴。列表预留滚动条且禁止单元格选择，透明选择图标。交互输出仅文件/编辑/错误，不记录视角、拾取及工具切换。

## 0.11.0 统一样式与显示设置
首次显示居中，不在最大化还原时重新定位。透明切面晶体图标，SVG/ICO 共用源；主题库 theme.py 集中管理控件/图标按钮/工作区标签页/数值步进按钮，数值框右侧上下分区参照 studio。工具按钮默认透明，保留悬停反馈；除专用展开按钮外隐藏菜单 V，原子坐标展开使用三点。方向轴采用 a 红/b 绿/c 蓝；元素色仍按 OVITO VESTA 主题，未知元素灰色。双空间预览以晶胞包围球计算固定比例，旋转不自动缩放。晶格参数符号斜体。右键视口→显示样式，含晶格/原子两个工作区风格标签页，可应用或取消未应用的修改；这些设置仅影响当前窗口显示，不改变结构。底部改称输出。

2026-11-14：参考项目工作区实际使用 SlantTabBar 自绘上圆角、平底连接页面，不能只仿 tab_css 或添加下划线。CrystalX 改用独立 WorkspaceTabBar；显示样式/坐标窗口共用主题自定义标题栏，去掉菜单“显示样式”的省略号。

## 0.12.0 显示与弹窗
弹窗统一圆角边框及中文按钮，背景 #f1f3f2、白色内容页，标签条跟随弹窗背景。按钮细边框、步进中线、标题内容分界、滑条未选段独立配色。视口与工具区纯白；输出下方去边线。透视图标为一致投影立方体，软件标志简化，方向轴缩短。已选原子列表背景及选择按钮高亮。顶部最右独立复制图片，保持中央按钮位置，复制纯场景 ARGB 透明图片至剪贴板。
原子材质改为球面法线 Lambert/Blinn 光照，远处淡化采用颜色雾化而非半透明。VESTA 具有完整球面网格、光照材质及深度缓冲；当前仍为缓存球面图像按中心深度排序，球体交叠的逐像素遮挡仍与真实三维渲染有差别。参考 https://jp-minerals.org/vesta/en/doc/VESTAch13.html 。

## 0.12.1 圆角与系统选择器修正
文件/目录选择恢复 Qt 原生系统窗口，不再主题化。自绘弹窗绝对禁止 setMask/QRegion 窗口遮罩：使用透明窗口、抗锯齿底色、内缩布局以及独立外框绘制层。参考 studio 的 StableTabs/RoundedSurface/TabPageOutlineOverlay，标签栏与页面使用稳定的兄弟控件布局，选中标签和内容页的圆角轮廓相连，控件位于内缩范围，不遮挡圆角。坐标窗口两个参考系共用页面以保留滚动。标题图标改为20像素并居中留白，底部状态栏加深为 #e0e6e2。

标题栏最小化/最大化/关闭按钮的悬停及按下区域统一为直角，关闭采用红色；弹窗关闭按钮共用同一样式。与弹窗本体圆角分别管理，不继承普通按钮圆角。

## 旋转性能修复 0.12.3
分离材质与雾化缓存，去掉每种雾化值逐像素重建；相机变换复用并跳过视口外原子。scripts/benchmark_viewport.py 提供离屏冷/热旋转基准。2026-11-14 本机：8 原子冷帧约695→89ms；512原子（8元素）冷帧13152→225ms，后续帧中位数214→35ms。离屏测量不代表真实屏幕帧率，更大结构仍受 QPainter 排序/绘制成本影响。

## 0.13.0 多结构工作区与终端（覆盖旧交互说明）
启动保留空结构工作区和终端（输出标签）。每次打开结构创建独立 StructurePage，名称为文件名；标签可左右拖动、关闭，未保存修改支持保存/丢弃/取消，各页模型、相机、选择及撤销记录隔离。关闭页时销毁其结构和弹窗。结构工作区固定铺满上方面板，不可浮动或关闭面板。
终端为下方固定标签面板，使用第二种圆角胶囊标签；上下分隔条调节两区比例，右上角隐藏与最大化/还原。查看→显示终端可恢复。编辑→结构→原子坐标取代列表标题三点入口；编辑→键保留入口，化学键功能尚未启用。
列表信息行高亮和原子选择独立；行选择只查看信息，图标默认叠加/再次点击取消，无需 Ctrl。画布单击空白不清空，所有工具双击空白清空，双击原子按原有 Ctrl 规则选择。轴色加深、左预览箭头变细、默认晶胞线宽1.5、菜单紧凑化、三点按钮无框、文件菜单等整高矩形反馈。
验证新增 scripts/check_workspaces.py，覆盖独立历史/排序/关闭保存取消/终端隐藏最大化/选择逻辑。

## 0.13.1 面板边框与空白启动页
标题菜单按钮改为52×30，并在标题栏下方预留1像素分界线。工作区与终端分别置于独立1像素细边框容器，隐藏/最大化操作作用于整个容器以免留下空框。工作区无结构时居中绘制最大360像素 SVG Logo，打开文件隐藏，关闭最后标签后恢复。终端关闭/最大化使用无框按钮，保留悬停/按下反馈。

## 0.13.3 面板圆角与可见侧边框
主工作区与终端使用 PanelFrame 自绘圆角底板，PanelOutline 在内容上层画完整外框。统一9像素圆角，外框 #9eafa5；分隔区外围留5像素，面板内容内缩6像素以保留角部及边线。禁止窗口遮罩，面板自身及子控件均不 setMask。隐藏/最大化仍作用整个包裹容器。已检查空白/打开结构截图及左右边线像素。

## 0.14.0 外层窗口与结构编辑（覆盖旧坐标入口说明）
外层 MainWindow 用 WindowShell 透明背景自绘圆角底板、轻阴影和独立上层外框，不使用遮罩。QMainWindow 必须用 setContentsMargins 内缩内容，不能用内部 layout 的 margins 替代。主工作区及终端边框0.7px，分隔外围3px；结构标签条加深，表头透明，空页增加 CrystalX。标题菜单高度36px接触可用边缘，下方独立1px分界线；禁用图标显式灰色。
编辑→结构直接打开 StructureEditor，第一标签晶格，第二标签原子。原子页以动画分段滑块切换 Cartesian/Direct，共用表格保留滚动，未应用修改先提示应用。表格行选择仅作用于本表，与左侧信息行及原子选择完全独立。元素/标签/坐标修改显式应用并支持撤销。
lattice_edit 是不依赖 Qt 的领域模块。直接修改六个晶格参数保持原分数坐标及晶格整体朝向；输入矩阵 P 按 VESTA 列系数约定，新行晶格 L'=PᵀL，分数坐标重新计算，原笛卡尔位置不变。这是基矢变换，不自动增删超胞原子。快照命令校验失败不修改原结构。
VESTA 初始键使用 style.ini 中的元素对及最小/最大距离规则并搜索周期邻胞，非显示球半径直接决定。CrystalX 当前化学键入口仍禁用，尚未实现自动成键。参考官方文档 VESTAch8.html、VESTAch16.html。

## 0.15.0 自动成键与编辑布局（覆盖旧的未启用成键说明）
领域模块 bonds.py 使用 Gemmi 共价半径（非显示球半径），默认距离在0.4 Å至1.2×半径和之间判断显示键。用倒易矢量求邻胞范围覆盖倾斜/短晶胞，笛卡尔分箱搜索，键段裁剪至单位晶胞并去重，支持同一源原子的周期镜像成键。这是几何启发式，非键级/电子结构判定，也不是复用 VESTA 的 style.ini 默认表。显示不改变模型及导出文件。
视口用晶格/坐标/元素/搜索阈值缓存键搜索结果，旋转及选择复用缓存；按端点复用投影、按元素/宽度复用画笔，键在球体轮廓处截断。仍沿用 QPainter 深度排序，非逐像素深度缓冲；密集多键结构成本仍高于只显示球体。
显示样式第三页为键，可设置显示、半径和倍率、最短键长、键宽、元素双色或统一颜色；编辑→键直接打开此页。config/default/app.json 的 bond_settings 可被 custom/app.json 同名键整体覆盖，每结构页面显示设置独立。
结构标签栏需绘制整个 StructureTabs 顶条背景 #cbd6ce，不能只填充宽度随标签数量变化的 QTabBar。正常窗口标题/状态栏分别上/下圆角，最大化外框/背景/标题/状态全部直角且无阴影。
StructureEditor 晶格参数两栏，左abc右角度，无分隔；矩阵只标变换矩阵。参数/矩阵失焦重建预览副本，不累积矩阵；应用统一提交晶格与原子草稿为一次快照，关闭丢弃未应用值并恢复视口。原子参考系为46×26动画开关，名称旁置；表格无网格、单元格独立选择，编号保持只读。重置相机的屏幕上方向使用c在视平面内的投影。

## 0.15.1 VESTA 默认搜索范围（取代0.15.0半径启发式）
已只读核对官方稳定版 VESTA 3.5.8 安装包 style.ini 的 SBOND：914条范围、912个无序元素对，H–O和D–O各有两段，Si–Si 0–2.6 Å，Si–O 0–1.99002 Å，Na–Cl 0–3.39412 Å。原始安装包/ini仅保留ignored output，不纳入项目分发；config/default/bond-ranges.json独立记录数值范围和来源。默认搜索严格按表，不为缺失元素对回退共价半径规则。只复用距离范围，不宣称复现VESTA的递归扩展/氢键绘制样式。
视口每页可独立修改bond_ranges；显示样式的键页列出结构中元素组合及其范围，未列组合默认停用，可手动启用。多段范围保留，0距离重合点不成键，缓存键包含完整范围表。移除旧半径倍率/全局最小距离控件和配置。
StructureTabs整条底板改上圆角；可关闭WorkspaceTabBar不再自绘矩形底色，使用父底板。晶格参数网格只有两个输入框列stretch，标签列按内容宽度，水平间距6px。

## 0.15.2 键编辑与显示外观分离（覆盖旧入口说明）
编辑→键打开单独 BondEditor 弹窗（bond_editor.py），元素对/启用/最小最大键长仅在此编辑。显示样式→键只包含显示开关、宽度、元素双色/统一颜色及颜色设置，不应出现原子或搜索参数表。外观应用只更新appearance并重绘，不改bond_ranges或触发键搜索。
BondEditor绑定各StructurePage，重复打开可见弹窗时复用，关闭后重新打开按已应用范围重建草稿；元素集合改变时刷新表，单纯原子选择变化不覆盖编辑内容。结构切换隐藏、关闭结构关闭弹窗，防止残留窗口编辑其他文档。

## 0.15.3 主工作区标签条触边
workPanel布局边距改为左/上/右1px、下5px，标签条延伸到面板内侧，不留5px空带。StructureTabs背景透明，深色条及首个选中标签左上角使用8px半径，衔接面板9px外圆角。PanelOutline继续置顶绘制完整细边框，标签条不得遮边；终端边距维持原样。

## 0.15.4 重置视角和标签圆角（覆盖旧重置说明）
view_orientation.py提供晶格相对标准浅斜视：以真实c为上、b在垂直c平面中的投影为右，叉乘为朝向观察者；方位偏转atan(1/3)、仰角atan(1/6)，表现为a左下朝前、b右、c上。角度是本项目用于参考VESTA风格的选择，非从VESTA源码或官方默认矩阵提取；官方手册ch10规定晶格/倒易矢量定义投影和上方向，ch4的Fit to Screen为缩放和居中。不要宣称完全复现VESTA默认矩阵。方向计算与Qt解耦，支持全局旋转和倾斜晶格。
reset_view恢复此相机及正交投影，再按当前视口、晶胞和原子球体投影边界进行适配居中，边缘保留40px，不再要求zoom=1；重置后的拖动继续在当前矩阵累积。tests/test_view_orientation.py覆盖方向、正交性、行列式及晶格全局旋转不变量；集成检查覆盖宽/长/倾斜晶胞不裁切及零增量连续性。
主工作区标签两个上圆角、标签条底板、面板外框共享theme.PANEL_RADIUS=9。标签角部使用真实圆弧，面板上层外框及1px边距继续保留；弹窗标签样式保持6px。

## 0.15.5 标题菜单栏触顶（覆盖旧分界线要求）
用户取消标题菜单栏下分界线，titleChrome不再画border-bottom，布局下边距从1改为0。theme.TITLE_BAR_HEIGHT=32统一标题、菜单、撤销重做及窗口控制的高度；按钮不留上下悬停空白。
WindowShell普通窗口left/right/bottom仍15px，但top改10px，紧接9px阴影内可见边框；最大化所有边距1px。窗口控制右侧普通态额外5px避免其直角高亮进入外窗右上弧线，最大化为0。标题栏背景不泄漏至弹出菜单，圆角外框/阴影继续保留，不用遮罩。
已检查文件按钮普通态顶坐标y=10且顶像素为hover色，最大化y=1，并保存两态顶部悬停截图。

## 0.16.0 可见性、结构预览与表格编辑
顶部透视之前插入VisibilityMenu眼睛按钮，使用整行QCheckBox承载条目，轴/原子/晶格默认true，元素/编号/标签默认false。混合原子可见状态为圆角矩形填充，全部隐藏为未勾选；从混合/隐藏点击恢复全部，已全显点击隐藏全部。视口hidden存源原子索引，周期镜像同步，绘制/标签/拾取/框选及关联键忽略hidden。右键有选择才出现隐藏/删除；隐藏清空选择且不改模型，删除沿用可撤销结构操作和确认。拓扑修改及撤销/重做清除hidden，避免索引错配。
原子深度雾化上限0.25、透明度最低0.65，选中标记不淡化。图标按16至128多个原生尺寸渲染SVG并缓存，禁用仍显式灰色；复用同一QIcon。左双空间晶胞线宽1.6。
lattice_comparison.py独立绘制前/后两个可旋转缩放晶格，中间箭头；共同包围球尺度便于比较。右图灰虚线原始晶格、蓝实线参数中间晶格、黄实线矩阵最终晶格，最终基矢黑线箭头。矩阵变化时在参数阶段晶格基上绘制黑色整数格点，远点alpha更低；大范围按整数步长抽样点阵至约2200点，避免编辑时生成海量点。右上无外框问号按钮悬停/点击显示规则浮文，移开/再点关闭。
transform_basis领域函数新增整数系数约束（容差1e-8），仍要求可逆。参数先变保持分数，矩阵后变保持笛卡尔，L'=PᵀL。失焦比较原值，QAbstractSpinBox pendingEdit属性淡红，应用/取消/外部刷新复原；无效矩阵暂留最后有效预览并显示错误，点击应用弹主题化中文警告，原结构不变。
StructureEditor原子表7列：勾选、编号、元素、x、y、z、标签。勾选仅用于本表新增/删除，和单元格/视口/左列表选择无连接。全选支持混合状态；新增默认首元素、零坐标、T标志，删除按勾选；至少留1原子。草稿显式应用，源编号UserRole映射保留源flags，增删同数量也视作拓扑变更。当前坐标名称及短开关右对齐；表头与单元格居中。
BondEditor移除范围说明，顶部新建/删除/清除。新建默认当前元素，可编辑元素及距离；删除当前表格选中行，清除表内所有行，应用后同时清除已删除元素对范围而非恢复默认。表头最小键长/最大键长，数据居中。显示样式颜色仅呈色块（存储仍hex）。table_controls.CenteredCheckDelegate集中绘制居中暗边勾选框，theme统一普通checkbox/表格checkbox/混合填充。
新增scripts/check_visibility_editing.py覆盖隐藏状态、周期像过滤、勾选解耦、增删应用撤销、无效矩阵原子性、组合预览、键清除及颜色按钮；领域增可逆整数及组合坐标不变量测试。

## 0.16.1 渐淡减弱与键规则自动筛选（覆盖启用列规则）
原子深度渐淡改为opacity最低0.82、雾化最高0.15，选中标记仍不淡化。BondEditor只剩元素1/元素2/最小键长/最大键长四列，移除启用勾选框，表中配置的范围全部启用；未配置元素对不再生成停用占位行。
automatic_bonds可通过matched_ranges集合输出实际匹配的(pair,min,max)，在周期段裁剪前计算完整原子距离，并在几何去重前记录所有匹配区间。视口随搜索缓存此集合，键编辑按范围逐行隐藏没有匹配site的规则，不能仅按元素对是否存在判断。规则隐藏不删除底层数据，结构改变可恢复可见。新建/修改草稿pending时不筛隐藏，避免用户输入中行消失，应用后重筛；删除/清除仍清除对应规则。
25项领域测试含周期键完整距离、多区间重叠和去重下的规则匹配；集成覆盖四列表格、无匹配隐藏、匹配恢复、同元素对不同区间独立筛选。

## 0.16.2 结构编辑弹窗高度
结构编辑默认尺寸900×700（原900×830），减少纵向空白；晶格变化前后预览仍保持可旋转缩放，底部应用/关闭完整显示。已检查截图及结构编辑集成。

## 0.17.0 完整显示样式、范围及全局默认
空页WelcomeLogo通过SVG内存换色显示#c2c7c4，名称#bfc5c1；不修改assets原图及启动/标题图标。DisplayStyleDialog三页、980×720，顶部作用于：当前对象/当前结构/全局，底部左加载/导出/恢复默认/设为默认，右确定/应用/取消。预览独立CrystalViewport，表单变化只更新预览，应用才提交；取消保留之前已应用值。
晶格页分晶胞、方向轴与箭头两组及右侧预览。cell_line=0实/1划/2点/3点划/4双点划/5圆柱，宽度/直径用px，只有圆柱启用粗糙度/折射率/光泽。轴用线框箭头或立体箭头，方向标签独立开关、a/b/c色块、线宽、头宽/头长、材质，平面轴材质禁用。所有色块统一42×25圆角按钮。
原子页包含光泽/渐淡、原子/离子/范德华/自定义半径、显示比例、粗糙度/折射率、按元素或自定义颜色、边框色与px宽度。atomic-radii.json从VESTA3.5.8 elements.ini提取数值（atomic列2、vdw列3、ionic列4），离子半径为代表价态配位；无原始VESTA文件分发。三类表格半径乘0.42显示缩放，自定义半径直接以Å值乘显示比例。
键线型0实/1点/2划/3双色/4单色/5渐变；双色/渐变显示两个色块，单色线一个。双色和渐变可按元素或自定义两端颜色。仍与键搜索弹窗分离。
appearance.py是Qt无关校验/预设层，默认config/default/display.json；AppearanceStore用户默认config/custom/display.json，current为会话全局基线。全局应用影响所有打开/以后新开的页面，设为默认额外持久化；恢复默认加载已保存的全局默认到草稿，加载预设切到全局草稿，需应用。导出是完整全局预设，不导出对象局部覆盖。文件schema含format/version/settings，校验类型/颜色/范围并原子替换写入，不覆盖自带默认。
当前对象按属性分组仅修改所选源原子/键段/晶胞边，未选择对应类型时提示。当前结构/全局按实际改变字段更新并清理同字段局部覆盖。全局或当前结构明确显示原子时恢复隐藏原子；单对象显示恢复对应隐藏源原子。selection双击任意工具/选择工具单击：原子优先，再按投影线距离/深度拾取键与边，Ctrl叠加，空白双击清空。框选仍选择原子。边按12条编号，键按段索引；几何变化清理键覆盖/选择，拓扑变化及撤销重做清理对象覆盖以免错配。对象覆盖目前仅会话保存。
render_material.py共用半径/圆柱/箭头材质；sphere_material缓存增加粗糙度/折射率/光泽维度。折射率通过F0反射系数影响表面高光，粗糙度控制高光宽度与强度，仍为QPainter投影材质近似，不模拟真实光线折射/逐像素深度缓冲。旧球体fog缓存和相机变换复用保持；密集多键结构仍较慢。
新增tests/test_appearance.py和scripts/check_display_style.py：29项领域测试覆盖默认持久化、非法预设、半径和材质实际像素差异，集成覆盖对象/结构/全局隔离、新文档继承、预设读写、控件状态和所有线型预览。结构显示参数不计入POSCAR文档dirty历史。

## 0.17.1 作用范围文字背景
显示样式顶部“当前设置作用于”QLabel显式透明背景、无边框，避免全局QWidget浅色底形成色块；范围下拉框维持原控件样式。

## 0.17.2 Enter与颜色选择窗口
ColorButton显式setAutoDefault(False)/setDefault(False)，共用install_dialog_chrome也取消已存在QPushButton辅助按钮的自动默认行为，避免输入框Enter触发第一个色块/加载/清除等操作。颜色对话框保留Qt的颜色/屏幕取色/自定义色逻辑，用QColorDialog.create统一创建、原有getColor调用此工厂。
颜色窗口本地覆盖CONTROLS和stepper_css，标签和私有颜色面板/按钮区透明，十六进制QLineEdit与数值框统一细框。用仅针对QColorDialog上下文的ColorTranslator覆盖动态取色提示及标签，HTML显示为十六进制，确定/取消及取色/添加自定义按钮中文；不影响原生文件选择器。
Qt QColorLuminancePicker源码paintEvent的eraseRect在指针侧留白，单改QSS/Window palette无法去除。LuminanceSurface事件过滤只接管该控件绘制（无遮罩）：画渐变条/边框/指针，空白区域透明；鼠标和颜色同步仍交由Qt。依赖其Qt6私有控件类名，升级Qt需复跑截图与像素检查。
新增scripts/check_color_dialog.py覆盖字段Enter/小键盘Enter不弹色窗、聚焦色块Enter不误触发、鼠标正常打开、中文/动态翻译、十六进制输入更新、透明指针侧底色及确定/取消结果。29项领域测试及原界面/编辑检查通过。

## 0.18.0 直接编辑原子值与GGX材质（覆盖旧配色/半径交互）
主工作区标签条#e3eae5，默认晶胞颜色#637b6b；用户已保存的自定义颜色仍尊重。theme通过assets/combo-arrow.svg统一QComboBox::down-arrow与右侧drop-down布局，不影响此前不显示V的工具菜单按钮。
原子页移除atom_color_mode选择框，但保留该内部键兼容预设。默认色块显示当前选择首原子（无选择则结构首原子）的元素色，点击色块直接产生当前作用范围的颜色覆盖；未编辑则继续按各元素默认色。原子半径下拉仅原子/离子/范德华三个基础类型，当前半径数值始终可编辑。编辑数值自动转内部custom类型3，所选基础类型记录atom_radius_source；换基础类型（含同一项重新选择）恢复该类型默认数值，元素表不会改动。
半径UI显示名义Å值，为与默认球棍显示比例一致，直接输入转换内部atom_radius=UI值×0.42；内部旧custom预设按实际显示半径读取，并以÷0.42显示，未触碰值时保留存储精度，避免打开设置就改半径。颜色和半径覆盖遵从对象/结构/全局范围，默认元素色表与RADII保持只读。
之前材质是Blinn指数高光与经验放大F0，参数参与计算但不是Principled实现。现在material_math.py统一GGX分布、Smith遮蔽与Schlick Fresnel，alpha=roughness²，F0=((ior-1)/(ior+1))²，IOR=1时界面反射为零；在线性光空间计算，再转sRGB。球体与圆柱/箭头共用同一计算器，surface_shader按材质缓存系数/闭包，图像仍按材质缓存，雾化由Qt合成。仍是单光源不透明表面的投影近似，不具备Blender的环境路径追踪/真实透射/多重散射。参考Blender官方Principled BSDF手册关于微表面粗糙度与IOR的定义。
新增scripts/render_material_comparison.py生成output/material-comparison.png：粗糙度0.1/0.35/0.8，IOR1.05/1.5/2.4。32项领域测试覆盖F0、GGX峰值/离轴宽度、IOR和哑光像素、旧预设兼容；显示集成检查直接编辑半径/颜色、基础值切换和默认表不变，所有原界面/颜色/结构/多文档检查通过。

## 0.18.1 连续光泽与IOR范围
原子、晶胞圆柱及立体方向轴的光泽由开关改为0–1连续高光权重，默认1保持旧外观，0关闭高光；参与Fresnel反射权重及材质缓存，粗糙度仍独立控制宽度。旧布尔预设按False→0、True→1兼容读取。IOR保留1–3、默认1.5，UI提示说明其为常用非金属表面反光参数，非真实原子折射率或透射模拟。参考Blender官方Principled文档常见IOR约1–2且允许更高值。33项领域测试及显示集成检查通过。

## 2026-11-16 内核迁移评估（尚未接入生产）
新增 scripts/assess_kernels.py，测量完整周期成键、材质冷/热缓存及视口；独立 C++ 材质探针 native_material_probe.cpp，通过 ctypes 端到端测量，无新增运行依赖。45组参数像素差0；交替采样 Python94.85ms/C++28.16ms，约3.37倍，仅指首次球体生成。硅512/4096原子成键117.72/1178.85ms；短轴/倾斜与混合元素另测。旋转不重算成键且球体新增缓存miss为0，不能宣称内核迁移解决旋转卡顿。成键尚无C++试验，不给加速倍数。建议材质先、成键后，保留Python参考/回退，核对周期边界、去重及多段匹配语义。完整报告及原始样本位于 docs/performance/2026-11-16-*；探针DLL和profiles仅output。33项领域测试通过。

## 0.19.0 C++已接入（覆盖上文尚未接入说明）
球体、圆柱/箭头采样及成键候选计算已接入native/纯C++17内核，通过CPython自带C API绑定，无pybind11运行/构建依赖。setup.py build_ext --inplace明确构建，普通安装不需编译；构建wheel可设置CRYSTALX_BUILD_NATIVE=1。native_backend检查API_VERSION=2，模块缺失/加载失败/不兼容回退，实际计算错误不静默吞掉；CRYSTALX_DISABLE_NATIVE=1在进程启动时禁用。计算段释放GIL但仍同步，非UI异步。
保留python_sphere_image、python_cylinder_colors、python_automatic_bonds。C++成键只做候选/裁剪，Python仍按round(v,8)去重并转换输出，保证顺序/源ID/规则匹配；极小负数%1可为1.0，边界已兼容。MSVC /fp:strict，不使用fast-math。Qt图像/渐变/绘制及缓存不搬迁。
本机Windows x64/CPython3.14/MSVC14.38编译并实际启用，最终配对中位数球体55.69→4.47ms(12.46x)，100圆柱27.23→11.80ms(2.31x)，512原子成键183.78→37.40ms(4.91x)，4096原子1587.99→423.68ms(3.75x)，负载有波动不保证固定倍数。41项原生测试及六组界面检查通过；禁用时35项通过、6项原生专用跳过。docs/native-kernels.md记录接口/构建/限制；docs/performance/2026-11-16-native-samples.json保留原始样本。编译产物不入Git，其他平台和Python版本需另行构建验证。

## 0.20.0 XRD可视化
xrd_io.py独立于Qt，读取文本RAS的INT段和HEADER元数据，支持多个扫描、声明点数校验、UTF8/CP932/GB18030解码；保存第三列衰减系数但原强度不修正。两列XY/DAT/TXT/CSV支持注释及简单初始表头；不支持二进制RAW/RASX/XRDML。xrd_page.py为独立XrdPage及QPainter曲线，缩放/平移/恢复、对数、扫描切换、最近点、复制图片，无新依赖。MainWindow按页面类型管理菜单与生命周期，DisplayStyle全局应用只遍历结构视口，XRD没有伪造的StructureDocument。44项测试和check_xrd混合工作区检查通过。用户随后提供外部研究目录的完整路径，已只读实测BTO-13_10-110_1.ras：1扫描10001点，10–110°、步长0.01°、counts，衰减系数全1，最大强度1181913.625位于46.47°。TwoThetaOmega作为耦合扫描横轴映射2θ，原始轴名仍保留。check_xrd.py可传实际文件路径生成output/xrd-real-linear.png和xrd-real-log.png，实际导入、绘图及退出检查成功；原数据不复制进仓库。

## 0.20.1 XRD绘图样式与透明导出
只读核对output/x_rheed/src/ui/components/plot_chrome.py的HoverToolbar及flux_view.py的_plot：参考重置/可见性/相机三键、右上悬停、无网格、单矩形框、左底刻度7px；本项目用plot_chrome.py集中图框#8a8a8a/刻度#808080/文字黑色/12px及本项目SVG图标，Qt绘图独立实现。屏幕画布白色；XrdPlot.draw_plot复用export_image渲染，ARGB透明初始画布且不填背景，包含完整坐标文字与曲线、排除子控件工具栏。复制setImage与右键PNG导出均走此路径，默认2倍像素。Intensity为默认纵轴名称，有单位追加；对数指数用小字体绘制避免Unicode上标缺字。check_xrd验证屏幕内部白像素、导出内部/外部alpha0、工具栏不影响图像、PNG回读/剪贴板、可见性，并用BTO真实文件核验截图。

## 0.21.0 科学绘图与成功打开目录记忆（覆盖此前QPainter/无绘图库说明）
SessionState独立读取config/custom/session.json，MainWindow在结构/XRD成功完成打开后调用opened；失败/取消不写。文件选择器共用directory，重启保留，可注入SessionState用于测试，不修改default配置。原目录不存在回退默认。
新增matplotlib>=3.10,<4。XrdPlot容纳FigureCanvasQTAgg，scientific_figure集中构图，数据层加四个透明坐标轴覆盖层实现独立样式。默认Times New Roman11pt、黑色、白底、左/下轴；config/default/plot.json为默认设置。屏幕与PNG/SVG/PDF共享Figure，透明导出同时处理figure/axes/图例面色，保留图例边框，不导出Qt悬停工具栏；PDF嵌入TrueType、SVG保留常规文字。零/负值在对数数据变换中mask断线，非clip伪线。
PlotStyleDialog左导航四分类、右滚动内容，axes内再切换左下右上；图内右键默认general，轴区右键默认axes对应side。所有样式集中此处，原顶部log勾选移除。一般字体/字号/颜色/线宽可继承，标签另有覆盖。支持grid/box、四轴范围、方向/长度/宽度/自动或间距或数组刻度、定点/E/e格式与精度、log10间距、图例、线型及marker/face/edge。样式验证与试绘成功后才提交，错误内联、取消保留已应用值；纯样式调整保留缩放。
matlab_literals安全解析带符号/科学数值、嵌套数组/cell、行分隔、冒号序列及单双引号文本（支持双引号转义），展平成刻度/标签，不eval，不支持MATLAB函数或工作区变量。标签数字转文本，不足补空白，多余截断；空字段为auto，显式{}或[]可清空；输入至多10000项。Mathtext支持本次要求的Greek/rm/mathscr/bf/{}和上下标，非完整外部LaTeX引擎，不调用TeX，普通文字Times或用户字体、数学字体STIX。风格只在当前XRD页会话保留，未承诺跨启动持久化绘图样式。
新增tests/test_plot_style.py与scripts/check_publication_plot.py，核验解析/代码拒绝、继承、四轴、公式、图例、marker、单位、数值格式、log间距/零值、目录跨重启/格式/失败、导航初始位置、事务及缩放保留、透明图例/背景、PNG/SVG/PDF与剪贴板。BTO真实10001点也已验证；参考图和原始数据不纳入仓库。

0.21.0最终验证：52项测试全部通过，check_publication_plot、check_xrd（含BTO真实文件）、check_workspaces、check_ui通过；已检查设置窗口与真实曲线截图。

## 0.21.1 绘图空白与高DPI修复
原固定position=[.13,.16,.74,.71]预留约26%宽/29%高，且旧布局只会缩小图框不会收回空白。改为8px基础边距，用各轴tightbbox相对图框bbox的装饰尺寸迭代计算位置，默认只给左下标签实际空间，四轴及大字号亦保留完整。另发现复用FigureCanvasQTAgg但更换Figure后canvas的device_pixel_ratio未变化，Qt不会再次更新新Figure dpi；install_figure显式set_dpi(96*ratio)，统一rebuild/apply路径，避免高DPI物理缓冲区尺寸小于控件。
新增默认横/竖窗口图框占比与标签不裁切测试，check_xrd校验实际physical画布尺寸；100%/150%/200%缩放检查均通过，BTO真实数据和publication样式/导出检查通过。check_xrd注入独立SessionState，避免自动测试修改用户目录记录。

## 0.22.0 紧凑样式、多曲线与配置（覆盖旧图例和刻度交互）
PlotStyleDialog左导航28px，字体列表使用普通UI字体和22px行，弹出宽244px；字号/数值140px、字体230px、文本330px、颜色28×28。四轴内WorkspaceTabs再分轴线与范围/刻度/轴标签。继承文案为使用通用设置/使用坐标轴设置。轴label=None表示数据默认，编辑框显示有效值；空字符串表示显式隐藏。tick_mode由数组优先、间距其次、自动最后推导，旧键保留兼容但无UI；数组非空禁用间距，[]显式清空。
PlotCurve保存x/y/style/label/visible/points。每扫描独立曲线列表，添加文件曲线默认plot N；图例默认显示无框。各曲线草稿独立暂存、切换编辑与选择；未改变curve节的轴/通用修改不得误写当前曲线。单击选择、双击/右键标注最近点，CurveSelection是Qt叠层，导出不包含选择效果。曲线右键复制、图内粘贴及Canvas Ctrl+C/V使用自定义MIME，校验有限数值/长度；源继承颜色和线宽复制时物化，携带标点与名称，目标其他样式及bounds不变。文本输入不接管快捷键。
上下文菜单全部配图标，重置视图首项；轴含线性/对数快捷切换，图例/轴无图片复制或导出，空图内保留图片操作和添加曲线原生文件选择器。成功添加文件/加载配置更新SessionState。
PlotDefaults读写config/custom/plot.json；plot_presets使用带format/version的JSON原子写入，完整校验样式及可选逐曲线名称/样式，不写x/y研究数据。加载仅改草稿，设为默认先应用再持久化，后续新图/重启继承，不广播已有图。默认文件损坏警告并回退自带设置。
57项单元测试通过；check_plot_curves覆盖真实Ctrl+C/V、多曲线隔离、菜单/命中、标注、紧凑字体弹出框、数组优先和默认持久化；check_publication_plot新增配置加载目录记忆，check_display_style验证共用正方形色块兼容。

## 0.35.0 统一曲线、绘图历史与可编辑文件（覆盖早期无历史/标签不入模板说明）

PlotCurve新增稳定uid、source_id、role、metadata、legend_visible、expression、fill_baseline。派生fit/smooth/profile:N通过source_id关联源曲线，数值作为正常曲线存储；轮廓填充基底随派生曲线复制/删除/改色。源peak_analysis保留contours但contour_curves标记避免旧叠加重复绘制。分析重新运行更新相关曲线的数组，保留用户样式/名称；关闭显示隐藏派生线。修改实际扣底使相关派生线过期隐藏。删除源线仅解除关联，不删除独立结果。

LegendEntriesDialog按uid设置legend_visible，与visible分离。scientific_figure维护legend_curve_indices用于图例命中和双击编辑，不能按所有曲线索引直接zip。曲线删除关闭绑定索引的编辑器和分析弹窗，避免旧窗口操作到移位/不存在的曲线。粘贴分配新uid并清source_id，保留源metadata；膜厚窗口切换曲线时按各自metadata恢复波长/坐标类型默认，不借用目标图其他曲线的信息。

PlotHistory每扫描维护committed/history/redo_history，上限100；深复制可变样式/处理状态，x/y数组只读复用，更新派生数组采用替换而非原地修改。记录曲线/样式/分析标记/可见性/范围/图例位置；拖动图例和平移在释放时提交，滚轮提交视图历史。MainWindow按钮/Canvas快捷键接当前页撤销重做；文本框保持原生文本历史。历史不序列化进图文件。

expressions.py使用受限AST数值运算，无eval/exec。支持常用numpy数学函数（大小写不敏感）、^、Mathematica []调用、末尾{变量,最小,最大}优先于第二行域；函数单变量1501点、x/y隐式方程350²网格零等高线。方程纵域为当前y范围，多个分支生成多曲线；这不是完整Mathematica，不支持任意符号求解或外部代码。

plot_document.py定义CrystalX.PlotDocument v1，扩展.cxplot，原子替换JSON写入。每扫描保存原始XYScan及曲线/样式/范围/图例锚点/当前选择/模板名称；所有数据嵌入，无外部数据依赖。外部文件逐字段校验，拒绝非有限坐标、重复uid等，恢复仅读取数值，不执行expression。活动扫描按对象身份定位，不能用dataclass相等性查index（扫描内容可能完全相同）。模板路径不写入文件，避免携带机器相关写入位置。

文件菜单保存/另存为支持图文件；导出POSCAR/图片/矢量图分组，图内导出子菜单含剪贴板/文件/SVG/PDF。模板write_plot_config保留显式轴label，清除min/max，加载配置尊重其显式标签；None仍为按扫描自动命名。README写明此新规则覆盖旧行为。

Qt右键日志异常已独立复现为QWindow无window()；runtime仅对QWidget调用。math_ui所有8个拥有QPainter的paintEvent使用with确定释放，数学表格选中态按浅绿配深字，不取系统白色HighlightedText。检查包含QWindow/QObject ContextMenu、实际嵌套菜单、膜厚+标签修改顺序。

## 0.35.1 低计数宽峰拟合

实际rc_68.8562.cxplot两条数据均2401点、步长0.001°、噪声MAD估计约1.09 counts。旧1.5采样点种子平滑保留细噪声极值，第一条局部多峰拟合不收敛；第二条被自动突出度约5.47和固定raw R²>=0.65挡掉。用宽峰初值拟合原始数据可收敛，不能把此文件认定为无峰或数据损坏。

peak_fit.fit_peaks先保留原流程；失败/无峰且n>=49、ptp(y)<25*noise时，用sigma=max(3,min(24,n/100))采样点生成宽峰种子，自动阈值按高斯滤波噪声衰减估计，用户显式prominence仍优先。宽峰种子要求宽度>=4sigma采样步长。优化目标仍是原始y，不使用平滑数据替换原始拟合。raw R²<0.65时仅宽峰重试允许继续，需raw R²>0、趋势R²>=0.85及相对线性基线的BIC增益>10；峰高原有3noise约束仍保留。报告R²不替换为趋势R²，UI明确低信噪比提示。它是有约束的识别规则，不证明物理峰型唯一或提供参数不确定度。

实际不对称伪Voigt结果：34.2038248°、FWHM 0.4776091°、raw R² 0.5901317；34.6091315°、FWHM 0.4543926°、raw R² 0.5291949。原文件只读校验和不变；scripts/check_low_count_fit.py接受外部cxplot路径，验证实际Qt分析、独立模型线、保存回读；生成图仅output，不把研究数据提交Git。110项测试通过，含合成低计数宽峰和纯噪声拒绝。

## 0.36.0 绘图单位自动准备与RASX

用户授权按步长/速度推算计数率；确认XRR的q_z是横轴，纵轴保留强度。plot_units.prepare_scan只准备绘图副本，XYScan原始扫描保留在page.scans。XRD/RC counts按dt=step/speed（deg/min乘60）除以dt，metadata更新counts/s并记录CRYSTALX_COUNTS_TIME_S及转换依据；cps已归一化不再除。缺有效参数保留原单位，不伪造标签。XRR角度按文件Kα1及单位换算4πsinθ/λ到Å⁻¹，2θ轴先除2；缺波长不套默认Cu，保留角度和说明。

XrdPlot.display_scan独立提供绘图轴默认文字和读数；曲线x/y是当前单位，背景、寻峰、膜厚及导出共用它。原始scan对象身份继续用于多扫描缓存。模板样式读默认标签时使用display_scan。膜厚识别1/angstrom为q_a；无需把q再当角度换算。FileInfo仍显示源文件信息，同时附绘图坐标、推算时间、倍数与缺失参数说明。

plot_units.prepare_state读取旧.cxplot时迁移曲线x/y、背景/填充、峰位置、膜厚标记、轮廓数组/范围及视野；原始scans不改。转换后曲线metadata保留当前单位，反复保存/读回幂等。用户手工写的图注文本不自动重写，避免覆盖内容。

xrd_io.read_rasx从zip直接读取DataN/ProfileN.txt与MesurementConditionsN.xml，不提取到用户目录。RASHeader并非完整扫描信息，必须以ScanInformation映射轴、步长、速度及单位，波长从HWConfigurations/XrayGenerator读取；RASX波长字段按该格式Å值映射。复用原RAS输入校验，三列衰减系数保留但不自行应用。文件/添加曲线过滤器支持.rasx。

115项测试及check_plot_units实际三个文件检查通过；XRD实例步长0.01°、5°/min→0.12s→8.3333倍，RC实例0.001°、1°/min→0.06s→16.667倍；XRR实际文件确认qz膜厚测试50nm与保存回读，原文件哈希不变。该时间转换是按文件声明及用户授权推算，不声称已对照原厂cps导出。

## 0.36.1 空图例保留
scientific_figure在legend.visible为true时始终创建Legend，即使handles为空；空对象不绘制导出边框。LegendHandle作为Qt透明鼠标叠层，空图例保留至少84×28px占位、浅色虚线边及双线手柄，普通图例悬停显示边与手柄。legend_rect统一命中空/非空区域；旧legend拖动继续生效。LegendEntriesDialog应用时将现有bbox位置固定为axes坐标anchor，不因清空条目而换位。叠层不在Matplotlib输出中，导出无占位。scripts/check_empty_legend验证全取消/恢复、右键入口、hover/drag及导出像素不变。115项单元测试通过。

AFM识别现状：afm_io前12行存在X Unit或Y Unit才进入read_unit_xy；完整双单位头、两列有限数值；X长度单位且Y单位pixels标记DATA_KIND=AFM，负像素数拒绝。这是高度分布启发式，不靠文件名，也不是通用直方图文件识别。

## 0.36.2 AFM线剖面与共享模板
afm_io.py单位表新增picometer/picometre/pm。完整单位头X/Y均为长度时归AFM profile，X长度/Y pixels仍为AFM distribution；AFM_TYPE区分，二者DATA_KIND=AFM、template_name=AFM，共享同一个模板，不创建Line专用模板。profile默认Distance(X单位)/Height(Y单位)，distribution仍Height/Pixel count；原始数值不变，负高度合法，长度-长度内容识别不依赖Line文件名。scan_info针对profile直接对高度列计算均值、极值、峰谷差、方差、相对均值Ra/Rq，注明剖面统计不是全区域；旧无AFM_TYPE的AFM文件仍按distribution兼容。
实际BTO10_261126_Z Height_Backward_002_Line_slanted.txt为248点、MicroMeter/PicoMeter；Region为128点、NanoMeter/Pixel，两者真实Qt打开、共用AFM模板及文件信息验证通过，116项单元测试通过。

## 0.36.3 图片比例拖动
PlotAspectHost新增AspectGrip，父对象为host，定位绘图矩形右下角，不在Matplotlib内容及导出中。globalPosition相对拖动初始尺寸计算ratio，范围沿用0.1–10；40ms定时节流重绘，拖动中history_locked，释放后提交单步历史。只改general.aspect，保留bounds及数据。双击设auto；拖动结束同步已打开PlotStyleDialog的比例字段，不覆盖其他草稿。原有自适应/4:3/1:1/16:9及自定义w:h设置继续沿用。check_plot_ratio_drag覆盖实际鼠标拖动、比例几何、草稿同步、undo/redo、导出像素宽高比、cxplot往返及双击恢复。

## 0.37.0 XRR周期辅助条纹识别

xrr_fringe.py领域模块analyze_fringes返回FringeAnalysis及PeakResult。完整输入建立均匀网格、正数log插值；保留零值比例用于噪声抑制而非给原始数据加常数。强动态范围下，以降至最大强度约1/50作为低角度强衰减排除建议，以局部log噪声或零比例判断高q尾部；这些是启发式范围，不是临界角物理拟合。

对建议区间的去趋势信号做Hann周期谱（8倍补零仅提高读数插值）和自相关确认，突出第二周期时提示多周期。平滑宽度period/60、趋势尺度0.8period，局部MAD阈值和>=0.55period候选间距，回到原始log平滑曲线寻找附近真实局部极大值。无明确峰顶、低局部信噪比、多周期、周期不一致或疑似漏峰时列待确认；不构造缺失峰。固定完整数据上的滤波尺度再按用户范围过滤，避免旧算法len(crop)/30导致裁剪时改变候选集合。默认prominence自然对数相对单位，用户显式可调；min/max宽度为检测信号宽度而非FWHM。

Peak新增默认status/reason字段，不改变原有XRD/RC结果默认可靠。XRR专用方法只在PeakFindingDialog额外注册，不加入全局PEAK_METHODS，避免把通用API默认为XRR。结果表增可信度/说明，FWHM列在条纹模式隐藏；CSV仍可导出空FWHM及状态/原因。算法判定可靠不等于物理真实性。source.peaks仅含可靠候选；待确认存peak_analysis.fringe_candidates，用空心菱形绘制，剪贴板/旧单位迁移同步校验转换该字段。平滑结果作为独立曲线，原始强度不改。

膜厚窗与旧detect_fringe_maxima包装共用核心，后者只返回可靠位置；默认建议范围，表第五列说明，待确认默认不勾选，用户可手动确认/删除/新增/调整级次。顶部和膜厚“自动识别”同范围/默认参数得到相同可靠位置；输入包含非默认平滑/扣底时实际检测统一使用display_y。load_rows一次提交勾选/说明避免候选临时全勾引入额外标记历史。

文献依据：Lammel et al., arXiv:2008.04626（FFT用于条纹周期/厚度，Gaussian拟合的是频谱）；SasView Kiessig Thickness Calculator；refnx反射率物理模型含背景/分辨率。当前方案为本项目混合识别规则，不声称文献给出同一算法，也未实现完整Parratt/Abeles层模型拟合。

121项测试通过：裁剪、采样密度、倒序索引、多周期、单调/白噪声拒绝及旧功能。实际BTO2 4可靠+3待确认，BTO10 7+2，BTO13 XRR_1 6+5；周期约0.02777/0.02198/0.01893 Å⁻¹，为估计而非膜厚真值。check_xrr_fringe_ui验证三个原始文件哈希不变、Qt默认方法、同入口结果、待确认排除、图文件往返；check_plot_documents显式选择fit测试通用模型曲线，不把XRR默认当fit。

## 0.37.1 主工作区关闭按钮统一
WorkspaceTabBar在closable及tabInserted时为每个标签安装TabCloseButton，直接绘制居中深色叉号，不使用Qt原生图标/主题选中态。按钮18×18，右侧留9px，文字左10右34；currentChanged、tabMoved、resize/tabLayoutChange及paint刷新几何，原生滚动箭头优先置顶。点击按当前tabButton对象查实时索引后发tabCloseRequested，避免排序后关闭错页。移除StructurePage独有按钮分支，绘图/结构使用同一实现；非closable样式弹窗标签不受影响。
MainWindow.close_tab使用page is None检查，允许最后一个文档关闭，空工作区logo由update_actions恢复。绘图关闭显式清理close_analysis、close_editors、框选及文件信息窗后再deleteLater。check_tab_closing在100%/150%实际点击混合标签直到零个、重开、排序、长标题溢出及双状态深色像素通过；check_runtime_stability通过。
