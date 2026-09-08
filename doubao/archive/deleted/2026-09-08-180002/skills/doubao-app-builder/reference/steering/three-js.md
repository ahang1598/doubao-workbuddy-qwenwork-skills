# Three.js r147 UMD 引入指南（3D 小游戏按需）

r147 是最后一个含 UMD `examples/js/` 的版本：经典 `<script>` 标签引入，全局 `THREE` 命名空间。无需 importmap、无需 `type="module"`。

## 基础引入

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/loaders/GLTFLoader.js"></script>
<script>
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  const loader = new THREE.GLTFLoader();
</script>
```

覆盖路径：`examples/js/{controls,loaders,postprocessing,objects,shaders,exporters,...}/<Name>.js`。

## extensions 隐式依赖（黑屏陷阱）

**`examples/js` 下各文件之间有隐式全局依赖，且按 script 标签顺序求值。漏引或顺序错会直接抛 `TypeError` 并中断整个初始化脚本——页面卡在 loading 或永久黑屏，且没有任何报错提示。** 用到 addon 时整段复制下方清单，不要只挑名字对得上的那几个。

## 后期处理（EffectComposer / Bloom 等）——整段复制，顺序不可调换

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<!-- EffectComposer.js 内部定义 THREE.Pass 基类，必须排在所有 *Pass 之前 -->
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/postprocessing/EffectComposer.js"></script>
<!-- 纯 shader 对象，供下面的 Pass 引用 -->
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/shaders/CopyShader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/shaders/LuminosityHighPassShader.js"></script>
<!-- 各 Pass 均为 class X extends THREE.Pass，依赖上面的基类 -->
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/postprocessing/ShaderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/postprocessing/RenderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/postprocessing/UnrealBloomPass.js"></script>
```

| 你要用 | 必须同时引入 |
|---|---|
| `EffectComposer` | `CopyShader` + `ShaderPass`（构造函数里立即用到） |
| `UnrealBloomPass` | `LuminosityHighPassShader` + `CopyShader` |
| 任意 `*Pass` | `EffectComposer.js`（提供 `THREE.Pass` 基类），且必须排在它之后 |

只引 `EffectComposer` + `RenderPass` + `UnrealBloomPass` 这三个是**错的**，会报 `THREE.ShaderPass is not a constructor`。

## 色彩管理（r147 默认 Linear，必须显式启用 sRGB）

```js
renderer.outputEncoding = THREE.sRGBEncoding;          // 输出 sRGB
texture.encoding = THREE.sRGBEncoding;                 // 颜色纹理（baseColor / albedo）
// 注意：normalMap / roughnessMap / metalnessMap 保持默认 Linear，不要改
```

未启用会导致 PBR 材质看上去发淡 / 过饱和。
