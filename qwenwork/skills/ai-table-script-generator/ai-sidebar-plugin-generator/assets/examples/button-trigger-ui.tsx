/**
 * 按钮触发插件示例 - UI Page
 * 功能：监听按钮字段点击事件，获取并显示当前记录数据
 */

import React, { useEffect, useRef, useState } from 'react';
import { initView } from 'dingtalk-docs-cool-app';

interface ClickEventData {
  baseId: string;
  sheetId: string;
  recordId: string;
  triggerTime: string;
}

interface RecordFieldData {
  fieldName: string;
  fieldValue: any;
}

interface RecordDataResponse {
  baseId?: string;
  sheetId?: string;
  recordId?: string;
  fieldData?: RecordFieldData[];
  error?: string;
}

function App() {
  const [ready, setReady] = useState<boolean>(false);
  const [clickEvent, setClickEvent] = useState<ClickEventData | null>(null);
  const [recordData, setRecordData] = useState<RecordFieldData[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initView({
      onReady: async () => {
        console.log('View is ready');
        setReady(true);

        // 监听按钮字段点击事件
        const off = Dingdocs.base.event.onButtonFieldClicked(handleButtonFieldClicked);

        // 组件卸载时取消监听
        return () => {
          off();
        };
      },
      onError: (e) => {
        console.error(e);
      },
    });
  }, []);

  const handleClear = () => {
    setClickEvent(null);
    setRecordData(null);
    setError(null);
  };

  const handleButtonFieldClicked = async (event: { baseId: string; sheetId: string; recordId: string }) => {
    console.log('button field clicked', event);

    // 记录点击事件信息
    const now = new Date();
    const timeString = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    setClickEvent({
      baseId: event.baseId,
      sheetId: event.sheetId,
      recordId: event.recordId,
      triggerTime: timeString
    });

    // 调用 service 层获取记录数据
    setLoading(true);
    setError(null);
    try {
      const result: RecordDataResponse = await Dingdocs.script.run('getRecordData',
        event.baseId, event.sheetId, event.recordId);

      if (result.error) {
        setError(result.error);
        setRecordData(null);
      } else if (result.fieldData) {
        if (result.fieldData.length === 0) {
          setError('该记录没有文本字段');
          setRecordData(null);
        } else {
          setRecordData(result.fieldData);
        }
      }
    } catch (err) {
      console.error('Failed to get record data:', err);
      setError('获取记录数据失败');
      setRecordData(null);
    } finally {
      setLoading(false);
    }
  };

  if (!ready) {
    return <div style={{ padding: '20px' }}>加载中...</div>;
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h2 style={{ fontSize: '16px', marginBottom: '16px', borderBottom: '2px solid #333', paddingBottom: '8px' }}>
        按钮触发插件示例
      </h2>
      
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '14px', marginBottom: '4px' }}>
          监听状态: <span style={{ color: '#52c41a', fontWeight: 'bold' }}>✓ 监听中</span>
        </div>
      </div>

      {!clickEvent ? (
        <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '4px', color: '#666', textAlign: 'center' }}>
          点击按钮字段后显示记录数据
        </div>
      ) : (
        <>
          <div style={{ marginBottom: '16px', padding: '12px', backgroundColor: '#f9f9f9', borderRadius: '4px', border: '1px solid #e0e0e0' }}>
            <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '8px' }}>点击信息:</div>
            <div style={{ fontSize: '12px', lineHeight: '1.8', color: '#333' }}>
              <div>• BaseId: {clickEvent.baseId}</div>
              <div>• SheetId: {clickEvent.sheetId}</div>
              <div>• RecordId: {clickEvent.recordId}</div>
              <div>• 触发时间: {clickEvent.triggerTime}</div>
            </div>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '8px' }}>记录数据:</div>
            {loading ? (
              <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '4px', textAlign: 'center' }}>
                加载中...
              </div>
            ) : error ? (
              <div style={{ padding: '20px', backgroundColor: '#fff2f0', border: '1px solid #ffccc7', borderRadius: '4px', color: '#cf1322' }}>
                {error}
              </div>
            ) : recordData && recordData.length > 0 ? (
              <div style={{ border: '1px solid #e0e0e0', borderRadius: '4px' }}>
                {recordData.map((field, index) => (
                  <div 
                    key={index} 
                    style={{ 
                      padding: '10px 12px', 
                      borderBottom: index < recordData.length - 1 ? '1px solid #f0f0f0' : 'none',
                      backgroundColor: index % 2 === 0 ? '#fafafa' : '#fff'
                    }}
                  >
                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>{field.fieldName}</div>
                    <div style={{ fontSize: '13px', color: '#333', wordBreak: 'break-all' }}>
                      {field.fieldValue || <span style={{ color: '#999' }}>-</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          <button 
            onClick={handleClear}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: '#fff', 
              border: '1px solid #d9d9d9',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            清除
          </button>
        </>
      )}
    </div>
  )
}

export default App;