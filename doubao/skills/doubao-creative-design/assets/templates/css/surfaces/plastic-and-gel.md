# 塑料与凝胶｜材质实现

目前已覆盖半透明塑料；凝胶／果冻尚无独立配方，不将塑料等同于凝胶。参数与共用表面层继续在[材质共用层](materials.md#surfaces.base)维护。

<a id="material.plastic"></a>

## 半透明塑料

风格标签：通用。

- 材质替换同时复制 root 材质变量、surface 表面声明及 texture/light 两个子层；保留目标形状的几何声明。
- 仅调 grain/alpha/blur 不会把一种纹理变成另一种材质。
- 毛玻璃与透明效果依赖背景；背后有图像或色块时再判断模糊强度。

[共用层](materials.md#surfaces.base)与下面的材质层一起使用；纹理以 asset:svg 引用本地资源，正式 HTML 按内嵌步骤展开。

```css
.vl-plastic {
  --vl-shadow: 0;
  --vl-alpha: .72;
  --vl-blur: 8px;
  --vl-grain: .14;
  --vl-edge: .96;
  --vl-highlight: .60;
  --vl-texture-size: 192px;
}
```

