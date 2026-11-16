# 可选 C++ 计算内核

0.19.0 已接入应用：球体材质、圆柱与立体箭头的材质采样、周期性成键候选搜索。Python/PyQt 继续负责界面、缓存、绘制和编辑历史。

## 源码安装与本机构建

普通安装不需要编译器，缺少扩展时自动使用 Python。项目虚拟环境已在本机编译并启用了扩展；重新启动软件即可使用。

需要构建的开发者，在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install "setuptools>=68"
.\.venv\Scripts\python.exe setup.py build_ext --inplace
.\.venv\Scripts\python.exe -c "from crystalx.native_backend import kernels; print(kernels.__file__ if kernels else 'Python')"
```

Windows 需要带 C++ 工具链及 Windows SDK 的 Visual Studio Build Tools；当前验证 Windows x64、CPython 3.14.7、MSVC 14.38。其他 Python/平台需使用相应环境重新构建并运行测试，不能直接复制本机 .pyd。Linux/macOS 构建分支使用 C++17 编译选项，尚未在本次任务中验证。

扩展基于 CPython 自带 C API，无新增运行依赖；纯计算内核不依赖 Qt，使用 C++17。明确执行构建时，编译失败会报错，不悄悄声称已启用。应用启动时不编译代码。

发布方如需生成含扩展的 wheel，在构建环境设置 CRYSTALX_BUILD_NATIVE=1，再构建 wheel；普通 Python 安装不设置此变量。MANIFEST.in 将 C++ 源码纳入源码包。编译产物、日志、测量输出不提交 Git。已检查纯 Python 与原生 wheel 分别不含/包含扩展；本次没有验证脱离源码目录的完整应用资源安装，当前仍按源码目录方式安装启动。

## 实现边界

- native/material.cpp：共享 GGX/Smith/Fresnel 光照计算，生成球体 BGRA 像素及33个圆柱颜色采样。QImage 包装、雾化、QLinearGradient/画笔与图像缓存仍由原有层管理。
- native/bonds.cpp：整数元素ID、距离平方阈值、周期镜像、笛卡尔分箱、候选距离和晶胞裁剪，按原有遍历次序返回。Python 继续执行精确 round(v,8) 去重、端点输出及匹配规则映射，以保持既有显示键编号与选择行为。
- native/module.cpp：批量复制与校验输入，计算时释放 GIL，再构造 Python 输出；不在计算段访问 Python 对象。不能把释放 GIL 理解成 UI 自动异步化，现阶段调用仍为同步。
- native_backend.py：启动时加载扩展，检查 API_VERSION=2。缺失模块正常回退；ABI/DLL加载失败或API不匹配记警告并回退。计算异常正常抛出，不使用静默回退掩盖错误。
- 原实现保留为 python_sphere_image、python_cylinder_colors、python_automatic_bonds，作为回退及一致性基准。未改变键搜索范围、材质定义或结构数据。
- 未启用 fast-math，Windows 使用 /fp:strict。成键边界容差和裁剪语义保持不变；Python对极小负数执行%1可能得到1.0，原生输入边界包含这一情况。

可以在启动前临时禁用扩展进行诊断：

```powershell
$env:CRYSTALX_DISABLE_NATIVE='1'
.\.venv\Scripts\python.exe -m crystalx
Remove-Item Env:CRYSTALX_DISABLE_NATIVE
```

此开关在进程启动时读取。修改扩展后要关闭使用该扩展的进程再重新构建，并重启应用。

## 同轮性能对照（2026-11-16）

以下测量使用最终接入路径，交替执行 Python/C++，球体和圆柱各15次、成键各5次，取中位数。包含调用、数据转换、图像复制及Python后处理；球体不走图像缓存，法线已初始化。原始样本见 [2026-11-16-native-samples.json](performance/2026-11-16-native-samples.json)。

| 工作负载 | Python ms | C++接入后 ms | 加速 |
|---|---:|---:|---:|
| 单个128×128球体 | 55.69 | 4.47 | 12.46× |
| 100个圆柱渐变（含Qt构造） | 27.23 | 11.80 | 2.31× |
| 成键搜索，8原子 | 4.46 | 1.10 | 4.06× |
| 成键搜索，512原子 | 183.78 | 37.40 | 4.91× |
| 成键搜索，4096原子 | 1587.99 | 423.68 | 3.75× |

测试仍在本机运行，后台负载未受控制；4096原子和早先测量间存在明显波动，因此保留全部样本，避免把不同轮次的耗时直接相除。这与前期 MinGW/ctypes 探针不同，当前使用 MSVC 编译的 CPython 扩展，不能简单把两轮加速倍数视作同一实验。

这些是内核/材质构建耗时，不是整机旋转帧率。旋转复用球体和成键缓存，大结构逐对象处理和绘图仍有开销。

## 验证与复现

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/benchmark_native.py
$env:CRYSTALX_DISABLE_NATIVE='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests
Remove-Item Env:CRYSTALX_DISABLE_NATIVE
```

启用扩展的41项测试通过：涵盖周期自成键、倾斜/短晶胞、多段范围、实际匹配规则、顺序及源编号、边界/重合/负坐标、随机结构、输入不变；球体多色与随机/边界材质参数、alpha、圆柱朝向、输入校验与并发调用。球体允许跨编译器最多1个8位通道值的误差，圆柱色标允许1/65535，几何坐标对照到小数点后11位。

禁用扩展时35项测试通过，6项原生专用测试明确跳过；六组现有界面、显示、结构、可见性、工作区和颜色窗口检查通过。
