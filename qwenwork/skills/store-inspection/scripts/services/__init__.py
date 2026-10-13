"""服务编排层：业务用例的核心实现。

依赖方向：
- 上游：commands 层通过 AppContext 调用本层
- 下游：infrastructure（dws_client / mapping_cache / config / sync_state）
        + domain（schema / filters / records / form_link_builder / exceptions）
        + utils
"""
