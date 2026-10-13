"""微信视频号页面 CSS 选择器常量。

基于 2026-04 实际页面 DOM 验证。使用标准 CSS 选择器语法（兼容 CDP）。
改版时只需修改此文件。

注意：
- 不使用 Playwright 专有伪类（:has-text(), :visible 等），CDP 不支持
- 需要按文本查找元素时，在代码中用 JS 遍历匹配，此处提供容器选择器
- 按钮文本匹配统一使用 BUTTON_TEXT_* 常量配合 JS 查找
"""

# ========== 登录 ==========
# 登录页面检测：被重定向到 login.html 时页面上的标识元素
LOGIN_PAGE_INDICATOR = 'div.title-name'
# 扫码登录二维码图片（iframe 内部）
QRCODE_IMG = ".login__type__container__scan__qrcode img"
# 已登录状态标识（创作者中心左侧导航栏的用户昵称）
LOGGED_IN_INDICATOR = ".finder-nickname"

# ========== 视频上传 ==========
# 文件上传 input（display:none，需通过 JS 设置文件而非点击）
FILE_INPUT = 'input[type="file"][accept*="video"]'
# 上传区域的拖拽容器（可见的上传按钮区域）
UPLOAD_DRAG_AREA = '.ant-upload.ant-upload-drag'
UPLOAD_CONTENT = '.upload-content'

# ========== 图文上传 ==========
# 图片文件上传 input（display:none，multiple，最多 18 张，单张 ≤ 20MB）
IMAGE_FILE_INPUT = 'input[type="file"][accept="image/*"]'
# 图片上传容器
IMAGE_UPLOAD_WRAP = '.post-upload-wrap'

# ========== 图文标题 ==========
# 图文标题输入框（普通 input，22 字符内）
IMAGE_TITLE_INPUT = 'input.weui-desktop-form__input[placeholder="填写标题, 22个字符内"]'

# ========== 图文描述 ==========
# 图文描述输入区域（contenteditable div，1000 字符内）
# 选择器与视频描述相同：div.input-editor[contenteditable]
IMAGE_DESC_INPUT = 'div.input-editor[contenteditable]'

# ========== 视频描述（标题） ==========
# 视频描述输入区域（contenteditable div）
TITLE_INPUT = 'div.input-editor[contenteditable]'
# 话题按钮
TOPIC_BUTTON = '.quick-btns .finder-tag-wrap'

# ========== 短标题 ==========
# 短标题输入框（在 .short-title-wrap 容器内）
SHORT_TITLE_INPUT = '.short-title-wrap input.weui-desktop-form__input'
# 短标题 placeholder 用于二次确认定位
SHORT_TITLE_PLACEHOLDER = '概括视频主要内容，字数建议6-16个字符'

# ========== 合集 ==========
# 合集选择区域
COLLECTION_DISPLAY = '.post-album-display'
COLLECTION_DISPLAY_TEXT = '.post-album-display .display-text'
# 合集下拉选项列表
COLLECTION_FILTER = '.post-album-wrap .filter-wrap'
# 创建新合集链接
COLLECTION_CREATE_LINK = '.post-album-wrap .create a'

# ========== 位置 ==========
LOCATION_DISPLAY = '.post-position-wrap .position-display'
LOCATION_NAME = '.post-position-wrap .location-name'
LOCATION_FILTER = '.post-position-wrap .location-filter-wrap'
LOCATION_SEARCH_INPUT = '.post-position-wrap input[placeholder="搜索附近位置"]'
LOCATION_OPTIONS = '.post-position-wrap .common-option-list-wrap .option-item'
LOCATION_HIDE_OPTION = '.post-position-wrap .option-item .name'

# ========== 链接 ==========
LINK_DISPLAY = '.post-link-wrap .link-display-wrap'
LINK_OPTIONS = '.post-link-wrap .link-list-options .link-option-item'

# ========== 活动 ==========
ACTIVITY_DISPLAY = '.post-activity-wrap .activity-display'
ACTIVITY_FILTER = '.post-activity-wrap .activity-filter-wrap'
ACTIVITY_SEARCH_INPUT = '.post-activity-wrap input[placeholder="搜索活动"]'
ACTIVITY_OPTIONS = '.post-activity-wrap .common-option-list-wrap .option-item'

# ========== 原创声明 ==========
# 原创声明复选框（如果页面上存在）
ORIGINAL_CHECKBOX_NEW = 'div.declare-original-checkbox input.ant-checkbox-input'
# 原创声明弹窗中的复选框
ORIGINAL_DIALOG_CHECKBOX = 'div.declare-original-dialog input.ant-checkbox-input'
# 原创类型表单
ORIGINAL_TYPE_FORM = 'div.original-type-form > div.form-label'
# 原创类型下拉选项
ORIGINAL_TYPE_OPTION = 'ul.weui-desktop-dropdown__list li.weui-desktop-dropdown__list-ele'

# ========== 定时发布 ==========
# 定时发表单选框容器
SCHEDULE_RADIO_GROUP = '.post-time-wrap .weui-desktop-radio-group'
# 不定时（value="0"）
SCHEDULE_RADIO_NOW = '.post-time-wrap input[type="radio"][value="0"]'
# 定时（value="1"）
SCHEDULE_RADIO_TIMED = '.post-time-wrap input[type="radio"][value="1"]'
# 定时发表的日期/时间选择器（选择"定时"后才出现）
SCHEDULE_DATE_INPUT = 'input[placeholder="请选择发表时间"]'
SCHEDULE_TIME_INPUT = 'input[placeholder="请选择时间"]'
SCHEDULE_DATE_PICKER = 'table.weui-desktop-picker__table a'
SCHEDULE_MONTH_LABEL = 'span.weui-desktop-picker__panel__label'
SCHEDULE_NEXT_MONTH = 'button.weui-desktop-btn__icon__right'

# ========== 发布/草稿按钮 ==========
# 按钮容器（包含"保存草稿"、"手机预览"、"发表"三个按钮）
FORM_BUTTONS_CONTAINER = 'div.form-btns'
# 发表按钮（通过 class 定位：primary 样式的按钮）
PUBLISH_BUTTON = 'div.form-btns button.weui-desktop-btn_primary'
# 保存草稿按钮（form-btns 内第一个 default 按钮）
# 注意：手机预览也是 default 按钮，需要通过文本区分
DRAFT_BUTTON_CONTAINER = 'div.form-btns'
# 按钮禁用状态 class
BUTTON_DISABLED_CLASS = 'weui-desktop-btn_disabled'

# 按钮文本常量（用于 JS 遍历匹配）
BUTTON_TEXT_PUBLISH = '发表'
BUTTON_TEXT_DRAFT = '保存草稿'
BUTTON_TEXT_PREVIEW = '手机预览'

# ========== 上传状态 ==========
UPLOAD_ERROR = 'div.status-msg.error'
# 删除已上传视频的标签（在 media-status-content 内）
UPLOAD_DELETE_TAG = 'div.media-status-content div.tag-inner'
UPLOAD_DELETE_TAG_TEXT = '删除'

# ========== 弹窗处理 ==========
# 通用弹窗容器
DIALOG_WRAPPER = '.weui-desktop-dialog__wrp'
DIALOG_TITLE = '.weui-desktop-dialog__title'
DIALOG_CLOSE_BUTTON = '.weui-desktop-dialog__close-btn'
# 弹窗遮罩层
DIALOG_MASK = '.weui-desktop-mask'
# 弹窗内的按钮容器
DIALOG_FOOTER = '.weui-desktop-dialog__ft'

# 弹窗按钮文本常量（用于 JS 遍历匹配）
BUTTON_TEXT_CONFIRM = '我知道了'
BUTTON_TEXT_CANCEL = '取消'
BUTTON_TEXT_SWITCH = '切换'
BUTTON_TEXT_SAVE = '保存'
BUTTON_TEXT_NOT_SAVE = '不保存'

# "将此次编辑保留?" 弹窗
EDIT_KEEP_DIALOG = '.common-dialog'
# 无权限弹窗标题文本
NO_PERMISSION_TITLE = '.no-permission-title'
NO_PERMISSION_CONTENT = '.no-permission-content'

# ========== 商品相关 ==========
COMMODITY_DIALOG = '.add-commodity-dialog'
COMMODITY_VISIBLE_DIALOG = '.sale-visible-dialog'

# ========== 向后兼容别名 ==========
# publish_video.py 等文件中仍在使用的旧常量名，
# 这些常量现在作为"文本标签"用于 JS 遍历匹配，而非 CSS 选择器。
# 后续重构时可逐步迁移到新命名。

# 合集（旧名 → 现在作为文本标签用于 JS 查找）
COLLECTION_LABEL = '添加到合集'
COLLECTION_OPTIONS = '.common-option-list-wrap .option-item'

# 原创声明文本标签（用于 JS 遍历 label/button 匹配）
ORIGINAL_CHECKBOX = '视频为原创'
ORIGINAL_AGREEMENT = '我已阅读并同意 《视频号原创声明使用条款》'
ORIGINAL_DECLARE_BUTTON = '声明原创'
ORIGINAL_DECLARE_BUTTON_NEW = 'button.weui-desktop-btn_primary'
ORIGINAL_LABEL_NEW = 'div.label span'
ORIGINAL_TYPE_DROPDOWN = 'div.form-content'

# 定时发布
SCHEDULE_LABEL_TEXT = '定时'

# 短标题
SHORT_TITLE_LABEL = '短标题'

# 发布/草稿按钮（旧名兼容）
DRAFT_BUTTON = DRAFT_BUTTON_CONTAINER
PUBLISH_BUTTON_DISABLED_CLASS = BUTTON_DISABLED_CLASS

# 删除确认按钮（文本标签，用于 JS 遍历匹配）
DELETE_CONFIRM_BUTTON = DIALOG_FOOTER
