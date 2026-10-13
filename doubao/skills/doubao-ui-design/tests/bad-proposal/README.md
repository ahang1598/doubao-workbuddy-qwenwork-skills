# publish preflight 的阳性对照

`proposal.xml` 里有一行 `<img href="cycle-cover.jpg">` —— **本地路径**。

飞书只接受公网 URL，本地路径会被**静默丢弃且不报错**：
发布会报「成功」，字节级对账也会通过（它只对 html5-block），
而回读出来是「封面图：无」。用户看到的是一篇没有封面的方案。

这份文件的职责是被 `publish.py` 的 preflight 拦下来。
它变绿了就说明那条校验没了。
