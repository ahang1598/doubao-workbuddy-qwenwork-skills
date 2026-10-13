import { useEffect, useState, useCallback, useRef } from 'react';
import { initView } from 'dingtalk-docs-cool-app';
import { Button, Select, LoadingCard } from '@ali/we-design-3';
import translations, { type TranslateKey, type Locale } from './locales';
import {
  PageContainer, FormArea, FieldGroup, FieldLabel, RequiredMark,
  SummaryBox, SummaryTitle, SummaryRow, SummaryLabel,
  ErrorBox, FooterButton,
} from './styled';

/**
 * 数据源插件配置页面主组件
 *
 * 开发指南：
 * 1. 在 state 中定义你的配置项（如数据库连接信息、筛选条件等）
 * 2. 在 FormArea 中添加对应的表单控件
 * 3. 在 handleNext 中收集配置并调用 saveConfigAndGoNext
 * 4. 如果需要调用后端接口，引入 utils/api.ts 中的 fetchLoginCode / callBackendApi
 * 5. 如果需要支持"更新模式"（编辑已有配置），在 useEffect 中通过
 *    getSyncConfig 读取已保存的配置并回填表单
 */
function App() {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [isUpdateMode, setIsUpdateMode] = useState(false);
  const localeRef = useRef<Locale>('zh-CN');

  // ── 国际化翻译函数 ──
  const t = (key: TranslateKey): string => {
    const locale = localeRef.current;
    return translations[locale]?.[key] || translations['zh-CN'][key];
  };

  // ── 插件初始化 ──
  useEffect(() => {
    initView({
      onReady: () => setReady(true),
      onError: (e) => {
        console.error('initView error', e);
        setError(t('init_failed') + String(e));
      },
    });
  }, []);

  // ── 数据加载 ──
  useEffect(() => {
    if (!ready) return;
    (async () => {
      try {
        // 获取当前语言
        try {
          const currentLocale = await Dingdocs.base.host.getLocale();
          localeRef.current = currentLocale as Locale;
        } catch {
          console.log('Failed to get locale, using default zh-CN');
        }

        // 开发指南：在这里获取登录凭证、加载初始数据
        // 开发时后端请求通过 Vite proxy 代理到 http://localhost:8080
        // import { fetchLoginCode, callBackendApi } from './utils/api';
        // const code = await fetchLoginCode();
        // const data = await callBackendApi('/your-endpoint', code);

        // 尝试读取已保存的配置（更新模式）
        try {
          const savedConfig = await Dingdocs.base.host.dataSource.getSyncConfig<Record<string, unknown>>();
          if (savedConfig && typeof savedConfig === 'object') {
            const config = savedConfig as Record<string, unknown>;
            if (config.selectedOption) {
              setSelectedOption(config.selectedOption as string);
              setIsUpdateMode(true);
            }
          }
        } catch {
          console.log(t('first_time_config'));
        }
      } catch (e) {
        console.error('Init failed', e);
        setError(t('init_error') + String(e));
      } finally {
        setInitializing(false);
      }
    })();
  }, [ready]);

  // ── 提交配置 ──
  const handleNext = useCallback(async () => {
    setError('');

    if (!selectedOption) {
      setError(t('required_fields'));
      return;
    }

    // 收集配置
    // 重要：这里的 config 会被 AI 表格平台序列化为 JSON 字符串，
    // 作为 params 字段传递给后端的 /api/sheet_meta 和 /api/records 接口。
    // 后端通过 params 中的 dataType 字段来决定返回哪个数据源的表结构和数据。
    const config: Record<string, unknown> = {
      dataType: 'demo',       // 对应后端 DataSourceRegistry 中注册的数据源 ID
      selectedOption,          // 你的自定义配置项，后端可从 params 中读取
    };

    try {
      // 保存配置并进入下一步（AI 表格将开始数据同步）
      await Dingdocs.base.host.dataSource.saveConfigAndGoNext(config);
    } catch (e) {
      setError(t('save_failed') + String(e));
    }
  }, [selectedOption]);

  // ── 示例选项数据 ──
  const demoOptions = [
    { key: 'option1', title: t('option_one') },
    { key: 'option2', title: t('option_two') },
    { key: 'option3', title: t('option_three') },
  ];

  return (
    <PageContainer>
      {initializing && <LoadingCard />}

      {/* 表单区域 */}
      <FormArea style={{ display: initializing ? 'none' : undefined }}>
        {/* ── 示例表单项：下拉选择 ── */}
        <FieldGroup>
          <FieldLabel>
            {t('select_datasource')} <RequiredMark>*</RequiredMark>
          </FieldLabel>
          <Select
            mode="filter"
            options={demoOptions}
            placeholder={t('placeholder_select')}
            value={selectedOption ?? undefined}
            onChange={(value) => {
              setSelectedOption(value || null);
              setError('');
            }}
            size="normal"
            maxHeight={200}
            disabled={isUpdateMode}
          />
        </FieldGroup>

        {/* 开发指南：在这里添加更多表单项 */}
        {/* 例如：Radio 单选、DateRangeSelector 日期范围、Input 输入框等 */}

        {/* ── 配置摘要 ── */}
        {selectedOption && (
          <SummaryBox>
            <SummaryTitle>{t('current_config')}</SummaryTitle>
            <SummaryRow>
              <SummaryLabel>{t('datasource_label')}</SummaryLabel>
              {demoOptions.find((o) => o.key === selectedOption)?.title}
            </SummaryRow>
          </SummaryBox>
        )}

        {/* ── 错误提示 ── */}
        {error && <ErrorBox>{error}</ErrorBox>}
      </FormArea>

      {/* ── 下一步按钮 ── */}
      <FooterButton style={{ display: initializing ? 'none' : undefined }}>
        <Button
          type="primary"
          onClick={handleNext}
          disabled={false}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {t('next_step')}
        </Button>
      </FooterButton>
    </PageContainer>
  );
}

export default App;
