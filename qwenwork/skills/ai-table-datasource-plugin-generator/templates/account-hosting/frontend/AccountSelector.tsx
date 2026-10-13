import { useState, useEffect, useCallback } from 'react';

interface Account {
  accountId: string;
  name: string;
}

interface AccountSelectorProps {
  /** 选中账号后的回调，accountId 为空字符串表示取消选中 */
  onSelect: (accountId: string) => void;
}

/**
 * 三方账号代管选择器组件
 *
 * 功能：列出已有账号、新建 / 重命名 / 删除账号，选中后将 accountId 回调给父组件。
 * 父组件需将 accountId 传入 saveConfigAndGoNext 的第二个参数：
 *   await Dingdocs.base.host.dataSource.saveConfigAndGoNext(config, { accountId })
 *
 * 自定义凭证字段：
 *   在 handleCreate 函数中，newCredentials 的 key-value 即为存储的账号凭证。
 *   后端将通过 context.credentials 接收到相同结构的数据。
 *   请按实际需求修改 credentials 的字段（默认示例为 username / password）。
 */
function AccountSelector({ onSelect }: AccountSelectorProps) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newAccountName, setNewAccountName] = useState('');

  // TODO: 按实际需求修改以下凭证字段，支持任意 key-value 结构
  // 示例：{ username: '', password: '' }  →  修改为 { apiKey: '' } 或 { ak: '', sk: '' } 等
  const [newCredentials, setNewCredentials] = useState<Record<string, string>>({
    username: '',
    password: '',
  });

  const loadAccounts = useCallback(async () => {
    setLoading(true);
    try {
      const list = await Dingdocs.base.host.dataSource.account.list();
      setAccounts(list);
    } catch (e) {
      console.error('加载账号列表失败', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  const handleSelect = (accountId: string) => {
    setSelectedId(accountId);
    onSelect(accountId);
  };

  const handleCreate = async () => {
    if (!newAccountName.trim()) return;
    // 校验凭证字段不为空
    const hasEmpty = Object.values(newCredentials).some(v => !v.trim());
    if (hasEmpty) return;

    try {
      const { accountId } = await Dingdocs.base.host.dataSource.account.create({
        name: newAccountName.trim(),
        credentials: newCredentials,
      });
      setShowCreateForm(false);
      setNewAccountName('');
      setNewCredentials({ username: '', password: '' });
      await loadAccounts();
      handleSelect(accountId);
    } catch (e) {
      console.error('创建账号失败', e);
    }
  };

  const handleRename = async (accountId: string, currentName: string) => {
    const name = prompt('请输入新名称', currentName);
    if (!name?.trim() || name.trim() === currentName) return;
    try {
      await Dingdocs.base.host.dataSource.account.rename(accountId, name.trim());
      await loadAccounts();
    } catch (e) {
      console.error('重命名失败', e);
    }
  };

  const handleRemove = async (accountId: string) => {
    if (!confirm('确认删除此账号？删除后无法恢复。')) return;
    try {
      await Dingdocs.base.host.dataSource.account.remove(accountId);
      if (selectedId === accountId) {
        setSelectedId('');
        onSelect('');
      }
      await loadAccounts();
    } catch (e) {
      console.error('删除账号失败', e);
    }
  };

  return (
    <div style={{ width: '100%' }}>
      {/* 标题栏 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '10px',
        }}
      >
        <span style={{ fontSize: '13px', fontWeight: 600, color: '#1a1a1a' }}>选择账号</span>
        <button
          onClick={() => setShowCreateForm(v => !v)}
          style={{
            fontSize: '12px',
            padding: '4px 10px',
            border: '1px solid #1677ff',
            borderRadius: '4px',
            background: 'transparent',
            color: '#1677ff',
            cursor: 'pointer',
          }}
        >
          {showCreateForm ? '取消' : '+ 新建账号'}
        </button>
      </div>

      {/* 新建账号表单 */}
      {showCreateForm && (
        <div
          style={{
            padding: '12px',
            border: '1px solid #e8e8e8',
            borderRadius: '6px',
            marginBottom: '10px',
            backgroundColor: '#fafafa',
          }}
        >
          <div style={{ marginBottom: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>账号名称</div>
            <input
              value={newAccountName}
              onChange={e => setNewAccountName(e.target.value)}
              placeholder="如：生产环境账号"
              style={inputStyle}
            />
          </div>

          {/* TODO: 按实际需求修改凭证输入字段 */}
          <div style={{ marginBottom: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>用户名</div>
            <input
              value={newCredentials.username}
              onChange={e => setNewCredentials(c => ({ ...c, username: e.target.value }))}
              placeholder="请输入用户名"
              style={inputStyle}
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>密码</div>
            <input
              type="password"
              value={newCredentials.password}
              onChange={e => setNewCredentials(c => ({ ...c, password: e.target.value }))}
              placeholder="请输入密码"
              style={inputStyle}
            />
          </div>

          <button
            onClick={handleCreate}
            style={{
              width: '100%',
              padding: '7px 0',
              fontSize: '13px',
              backgroundColor: '#1677ff',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            保存
          </button>
        </div>
      )}

      {/* 账号列表 */}
      {loading ? (
        <div style={{ textAlign: 'center', fontSize: '12px', color: '#999', padding: '12px 0' }}>
          加载中…
        </div>
      ) : accounts.length === 0 ? (
        <div style={{ textAlign: 'center', fontSize: '12px', color: '#bbb', padding: '16px 0' }}>
          暂无账号，请新建
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {accounts.map(account => {
            const isSelected = account.accountId === selectedId;
            return (
              <div
                key={account.accountId}
                onClick={() => handleSelect(account.accountId)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '9px 12px',
                  border: `1.5px solid ${isSelected ? '#1677ff' : '#e8e8e8'}`,
                  borderRadius: '6px',
                  backgroundColor: isSelected ? '#e8f0fe' : '#fff',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s',
                }}
              >
                <span
                  style={{
                    fontSize: '13px',
                    color: isSelected ? '#1677ff' : '#333',
                    fontWeight: isSelected ? 600 : 400,
                  }}
                >
                  {account.name}
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span
                    onClick={e => { e.stopPropagation(); handleRename(account.accountId, account.name); }}
                    style={actionBtnStyle}
                  >
                    重命名
                  </span>
                  <span
                    onClick={e => { e.stopPropagation(); handleRemove(account.accountId); }}
                    style={{ ...actionBtnStyle, color: '#ff4d4f' }}
                  >
                    删除
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  fontSize: '13px',
  border: '1px solid #d9d9d9',
  borderRadius: '4px',
  boxSizing: 'border-box',
  outline: 'none',
};

const actionBtnStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#999',
  cursor: 'pointer',
  padding: '2px 4px',
};

export default AccountSelector;
