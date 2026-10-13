/**
 * 按钮触发插件示例 - Service Page
 * 功能：监听按钮字段点击事件，获取并显示当前记录数据
 */

function getActiveSheetName() {
  const sheet = DingdocsScript.base.getActiveSheet();
  return sheet?.getName();
}

function getActiveSheetId() {
  const sheet = DingdocsScript.base.getActiveSheet();
  return sheet?.getId();
}

/**
 * 获取记录的前3个文本字段数据
 */
async function getRecordData(baseId: string, sheetId: string, recordId: string) {
  try {
    // 获取 Sheet
    const sheet = DingdocsScript.base.getSheet(sheetId);
    if (!sheet) {
      return { error: 'Sheet not found' };
    }

    // 获取 Record
    const record = await sheet.getRecordAsync(recordId);
    if (!record) {
      return { error: 'Record not found' };
    }

    // 获取所有字段
    const fields = sheet.getFields();
    
    // 筛选出文本字段并取前3个
    const textFields = fields.filter(field => field.getType() === 'text' || field.getType() === 'primaryDoc').slice(0, 3);

    // 获取这些字段的值
    const fieldData: Array<{ fieldName: string; fieldValue: any }> = [];
    for (const field of textFields) {
      const fieldName = field.getName();
      const fieldValue = record.getCellValue(field.getId());
      fieldData.push({
        fieldName,
        fieldValue: fieldValue || ''
      });
    }

    return {
      baseId,
      sheetId,
      recordId,
      fieldData
    };
  } catch (error) {
    console.error('getRecordData error:', error);
    return { error: String(error) };
  }
}

DingdocsScript.registerScript('getActiveSheetName', getActiveSheetName);
DingdocsScript.registerScript('getActiveSheetId', getActiveSheetId);
DingdocsScript.registerScript('getRecordData', getRecordData);

export {};