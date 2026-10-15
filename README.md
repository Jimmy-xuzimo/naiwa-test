# 中国奶娃大学

一个以虚构的「中国奶娃大学」为主题的整活网页项目，包含趣味跳转、3D 校门场景和离线渲染展示。

> **整活声明**
>
> **本项目为网友自制的娱乐整活项目，与南京传媒学院（CUCN）没有关系，不存在官方关联、合作或背书。**
>
> 「中国奶娃大学」是虚构名称。页面中的校名、校徽元素、角色语录及「录取专用章」仅作趣味展示，不代表校方立场，不提供任何招生、录取或学籍服务。学校信息请以 [南京传媒学院官网](https://www.cucn.edu.cn/) 为准。

## 页面

| 入口 | 内容 |
| --- | --- |
| [`index.html`](index.html) | 首页动画，结束后跳转至南传官网 |
| [`jump.html?jump`](jump.html?jump) | 3D 动画跳转页，需带 `?jump` 参数 |
| [`campus.html`](campus.html) | 可交互的 3D 校门场景 |
| [`film.html`](film.html) | 离线渲染图片与视频展示 |

域名：[中国奶娃大学.com](https://xn--fiqs8srwb9ipxt8d.com/)（以实际部署状态为准）。

## 本地运行

项目为静态站点，无需安装 npm 依赖或配置后端。安装 Git 和 Python 3 后执行：

```bash
git clone https://github.com/yuyx0407/naiwa-test.git
cd naiwa-test
python -m http.server 8000 --bind 127.0.0.1
```

打开 <http://127.0.0.1:8000/>。按环境可将 `python` 换为 `python3` 或 Windows 的 `py`；按 `Ctrl+C` 停止服务。

建议通过 HTTP 服务预览，避免直接打开 HTML 时的本地资源访问限制。3D 页面需要浏览器支持 WebGL，浏览现有成片无需安装 Blender。

## 常用参数

| 参数 | 作用 |
| --- | --- |
| `motion=full` / `motion=reduce` | 首页及 3D 页面强制完整或减弱动态效果 |
| `low` / `hi` | 3D 页面切换低、高画质 |
| `post` | 3D 页面开启可选后处理，性能随设备变化 |
| `blend` | 3D 页面加载仓库内的校门模型与 AO 贴图 |
| `jump` | 启用 `jump.html` 的跳转动画 |

参数示例：`campus.html?low`、`jump.html?jump&motion=full`。默认尊重系统的减弱动态效果设置。

## 技术与目录

- **前端**：HTML、CSS、原生 JavaScript。
- **实时场景**：Three.js、WebGL、程序化几何体与 Canvas 贴图。
- **离线成片**：Blender Cycles 渲染，图片与视频随仓库提供。

```text
├── index.html       # 首页
├── jump.html        # 3D 跳转页
├── campus.html      # 实时场景
├── film.html        # 成片展示
├── assets/          # 角色图片、模型、贴图及成片
├── vendor/          # Three.js、模型加载器与后处理代码
├── tools/           # 场景生成、烘焙、渲染与发布脚本
└── CNAME            # 自定义域名配置
```

## 开发

`jump.html` 由 `campus.html` 和生成脚本派生。修改共享场景后执行：

```bash
python -X utf8 tools/build_jump.py
```

该命令会覆盖 `jump.html`；跳转页专属逻辑应在 `tools/build_jump.py` 中修改。更换跳转目标时，同步检查首页、场景页及生成脚本中的链接、文案和 `noscript` 地址。

重新渲染成片需准备 Blender、Pillow、FFmpeg，部分分析工具还依赖 NumPy。`tools/` 中的制作脚本包含本机路径和 `/tmp` 路径，需先适配；PBR 源贴图未完整打包。`publish_film.sh` 使用的 `quarter` 命名也需与渲染脚本的 `threeq` 统一。

## 部署

可直接部署到静态托管服务，无需构建。使用 GitHub Pages 时，在 **Settings → Pages** 中选择 **Deploy from a branch → main → / (root)**。

Fork 后请删除或替换 `CNAME`，按需配置自己的域名、DNS 与 HTTPS，并更新 `index.html` 中的 `og:image` 地址。请保留整活与无关联声明。

## 素材与许可

- [Three.js](https://threejs.org/) 使用 MIT 许可；离线场景使用 [Blender](https://www.blender.org/) 制作，PBR 贴图来自 [Poly Haven](https://polyhaven.com/)（CC0）。
- CUCN 相关名称、标识及其他第三方素材的权利归相应权利人所有，趣味展示不代表获得官方授权。
- 仓库目前没有项目整体的 `LICENSE` 文件，第三方依赖或素材的许可不等于整个项目采用相同许可。

问题反馈与改进建议可提交 [Issue](https://github.com/yuyx0407/naiwa-test/issues) 或 Pull Request。
