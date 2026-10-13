/**
 * 国际化文案配置
 *
 * 支持语言列表：zh-CN, zh-HK, zh-TW, ja-JP, en-US, ko-KR, pt-BR, tr-TR, th-TH, id-ID, ms-MY
 * 通过 Dingdocs.base.host.getLocale() 获取当前语言
 */

export type Locale =
  | 'zh-CN' | 'zh-HK' | 'zh-TW'
  | 'ja-JP' | 'en-US' | 'ko-KR'
  | 'pt-BR' | 'tr-TR' | 'th-TH'
  | 'id-ID' | 'ms-MY';

export interface TranslateType {
  select_datasource: string;
  placeholder_select: string;
  current_config: string;
  datasource_label: string;
  next_step: string;
  init_failed: string;
  first_time_config: string;
  init_error: string;
  save_failed: string;
  required_fields: string;
  option_one: string;
  option_two: string;
  option_three: string;
}

export type TranslateKey = keyof TranslateType;

const translations: Record<Locale, TranslateType> = {
  'zh-CN': {
    select_datasource: '选择数据源',
    placeholder_select: '请选择...',
    current_config: '当前配置',
    datasource_label: '数据源：',
    next_step: '下一步',
    init_failed: '插件初始化失败: ',
    first_time_config: '首次配置，无已保存的配置',
    init_error: '初始化失败: ',
    save_failed: '保存配置失败: ',
    required_fields: '请完成所有必填项',
    option_one: '选项一',
    option_two: '选项二',
    option_three: '选项三',
  },
  'zh-HK': {
    select_datasource: '選擇數據源',
    placeholder_select: '請選擇...',
    current_config: '當前配置',
    datasource_label: '數據源：',
    next_step: '下一步',
    init_failed: '插件初始化失敗: ',
    first_time_config: '首次配置，無已保存的配置',
    init_error: '初始化失敗: ',
    save_failed: '保存配置失敗: ',
    required_fields: '請完成所有必填項',
    option_one: '選項一',
    option_two: '選項二',
    option_three: '選項三',
  },
  'zh-TW': {
    select_datasource: '選擇資料來源',
    placeholder_select: '請選擇...',
    current_config: '目前設定',
    datasource_label: '資料來源：',
    next_step: '下一步',
    init_failed: '外掛初始化失敗: ',
    first_time_config: '首次設定，無已儲存的設定',
    init_error: '初始化失敗: ',
    save_failed: '儲存設定失敗: ',
    required_fields: '請完成所有必填項',
    option_one: '選項一',
    option_two: '選項二',
    option_three: '選項三',
  },
  'ja-JP': {
    select_datasource: 'データソースを選択',
    placeholder_select: '選択してください...',
    current_config: '現在の設定',
    datasource_label: 'データソース：',
    next_step: '次へ',
    init_failed: 'プラグインの初期化に失敗しました: ',
    first_time_config: '初回設定、保存された設定はありません',
    init_error: '初期化に失敗しました: ',
    save_failed: '設定の保存に失敗しました: ',
    required_fields: 'すべての必須項目を入力してください',
    option_one: 'オプション1',
    option_two: 'オプション2',
    option_three: 'オプション3',
  },
  'en-US': {
    select_datasource: 'Select Datasource',
    placeholder_select: 'Please select...',
    current_config: 'Current Configuration',
    datasource_label: 'Datasource: ',
    next_step: 'Next',
    init_failed: 'Plugin initialization failed: ',
    first_time_config: 'First-time setup, no saved configuration',
    init_error: 'Initialization failed: ',
    save_failed: 'Failed to save configuration: ',
    required_fields: 'Please complete all required fields',
    option_one: 'Option 1',
    option_two: 'Option 2',
    option_three: 'Option 3',
  },
  'ko-KR': {
    select_datasource: '데이터 소스 선택',
    placeholder_select: '선택하세요...',
    current_config: '현재 설정',
    datasource_label: '데이터 소스: ',
    next_step: '다음',
    init_failed: '플러그인 초기화 실패: ',
    first_time_config: '최초 설정, 저장된 설정 없음',
    init_error: '초기화 실패: ',
    save_failed: '설정 저장 실패: ',
    required_fields: '모든 필수 항목을 완료하세요',
    option_one: '옵션 1',
    option_two: '옵션 2',
    option_three: '옵션 3',
  },
  'pt-BR': {
    select_datasource: 'Selecionar fonte de dados',
    placeholder_select: 'Selecione...',
    current_config: 'Configuração atual',
    datasource_label: 'Fonte de dados: ',
    next_step: 'Próximo',
    init_failed: 'Falha na inicialização do plugin: ',
    first_time_config: 'Primeira configuração, sem configuração salva',
    init_error: 'Falha na inicialização: ',
    save_failed: 'Falha ao salvar configuração: ',
    required_fields: 'Preencha todos os campos obrigatórios',
    option_one: 'Opção 1',
    option_two: 'Opção 2',
    option_three: 'Opção 3',
  },
  'tr-TR': {
    select_datasource: 'Veri kaynağı seçin',
    placeholder_select: 'Lütfen seçin...',
    current_config: 'Mevcut yapılandırma',
    datasource_label: 'Veri kaynağı: ',
    next_step: 'İleri',
    init_failed: 'Eklenti başlatma başarısız: ',
    first_time_config: 'İlk kurulum, kayıtlı yapılandırma yok',
    init_error: 'Başlatma başarısız: ',
    save_failed: 'Yapılandırma kaydedilemedi: ',
    required_fields: 'Lütfen tüm zorunlu alanları doldurun',
    option_one: 'Seçenek 1',
    option_two: 'Seçenek 2',
    option_three: 'Seçenek 3',
  },
  'th-TH': {
    select_datasource: 'เลือกแหล่งข้อมูล',
    placeholder_select: 'กรุณาเลือก...',
    current_config: 'การตั้งค่าปัจจุบัน',
    datasource_label: 'แหล่งข้อมูล: ',
    next_step: 'ถัดไป',
    init_failed: 'การเริ่มต้นปลั๊กอินล้มเหลว: ',
    first_time_config: 'การตั้งค่าครั้งแรก ไม่มีการตั้งค่าที่บันทึกไว้',
    init_error: 'การเริ่มต้นล้มเหลว: ',
    save_failed: 'บันทึกการตั้งค่าล้มเหลว: ',
    required_fields: 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด',
    option_one: 'ตัวเลือก 1',
    option_two: 'ตัวเลือก 2',
    option_three: 'ตัวเลือก 3',
  },
  'id-ID': {
    select_datasource: 'Pilih sumber data',
    placeholder_select: 'Silakan pilih...',
    current_config: 'Konfigurasi saat ini',
    datasource_label: 'Sumber data: ',
    next_step: 'Selanjutnya',
    init_failed: 'Inisialisasi plugin gagal: ',
    first_time_config: 'Pengaturan pertama, tidak ada konfigurasi tersimpan',
    init_error: 'Inisialisasi gagal: ',
    save_failed: 'Gagal menyimpan konfigurasi: ',
    required_fields: 'Harap lengkapi semua kolom wajib',
    option_one: 'Opsi 1',
    option_two: 'Opsi 2',
    option_three: 'Opsi 3',
  },
  'ms-MY': {
    select_datasource: 'Pilih sumber data',
    placeholder_select: 'Sila pilih...',
    current_config: 'Konfigurasi semasa',
    datasource_label: 'Sumber data: ',
    next_step: 'Seterusnya',
    init_failed: 'Permulaan plugin gagal: ',
    first_time_config: 'Tetapan pertama, tiada konfigurasi tersimpan',
    init_error: 'Permulaan gagal: ',
    save_failed: 'Gagal menyimpan konfigurasi: ',
    required_fields: 'Sila lengkapkan semua medan wajib',
    option_one: 'Pilihan 1',
    option_two: 'Pilihan 2',
    option_three: 'Pilihan 3',
  },
};

export default translations;
