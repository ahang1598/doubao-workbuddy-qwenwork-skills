/**
 * 批量修改字段插件示例 - Service Page
 * 功能：批量修改字段类型、隐藏/显示字段
 */

// 获取所有支持的字段类型
function getSupportedFieldTypes(): string[] {
  return [
    'text', 'number', 'singleSelect', 'multipleSelect', 'date',
    'currency', 'primaryDoc', 'unidirectionalLink', 'bidirectionalLink', 
    'checkbox', 'url', 'rating', 'progress', 'filterUp', 'formula', 'person', 'lookup',
  ];
}

// 获取所有支持的目标字段类型
function getSupportedTargetFieldTypes(): string[] {
  return ['text', 'number', 'singleSelect', 'multipleSelect', 'date', 'checkbox',
    'url', 'currency', 'person'];
}

// 获取指定表格的所有视图（带详细信息）
function getGridViewsWithDetails(sheetId: string) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  if (!sheet) {
    return [];
  }
  
  const views = sheet.getViews();
  return views.map((view: any) => ({
    id: view.getId(),
    name: view.getName(),
    type: view.getType()
  })).filter((view: any) => view.type === 'Grid');
}

// 获取所有表格
function getAllSheets() {
  const sheets = DingdocsScript.base.getSheets();
  return sheets.map((sheet: any) => ({
    id: sheet.getId(),
    name: sheet.getName()
  }));
}

// 获取指定表格的所有字段（带详细信息）
function getSheetFieldsWithDetails(sheetId: string) {
  const sheet = DingdocsScript.base.getSheet(sheetId);
  if (!sheet) {
    return [];
  }
  const fields = sheet.getFields();
  // 仅返回支持的字段类型
  return fields
    .filter((field: any) => {
      return getSupportedFieldTypes().indexOf(field.getType()) !== -1 
    })
    .map((field: any) => ({
      id: field.getId(),
      name: field.getName(),
      type: field.getType()
    }));
}

// 批量修改字段类型
async function batchModifyFieldTypes(
  sheetId: string,
  fieldIds: string[],
  targetType: string
): Promise<{ success: boolean; message: string; failedFields?: string[]; fieldChanges?: { fieldName: string; fromType: string; toType: string }[] }> {
  try {
    const sheet = DingdocsScript.base.getSheet(sheetId);
    if (!sheet) {
      return { success: false, message: 'SHEET_NOT_FOUND' };
    }

    const failedFields: string[] = [];
    const fieldChanges: { fieldName: string; fromType: string; toType: string }[] = [];
    
    // 遍历所有需要修改的字段
    for (const fieldId of fieldIds) {
      const field = sheet.getField(fieldId);
      if (!field) {
        failedFields.push(fieldId);
        continue;
      }
      
      const fieldName = field.getName();
      const fromType = field.getType();
      try {
        // 使用 updateFieldAsync 异步更新字段类型
        const fieldRes = await sheet.updateFieldAsync(fieldId, {
          type: targetType as any,
        });
        
        fieldChanges.push({ fieldName, fromType, toType: targetType });
        console.log(`字段 ${fieldName} 更新成功为 ${fieldRes.getType()} 类型`);
      } catch (error) {
        console.error(`字段 ${fieldName} 更新为类型 ${targetType} 时发生错误: ${(error as Error).message}`);
        failedFields.push(fieldName);
      }
    }
    
    if (failedFields.length > 0) {
      return { 
        success: false, 
        message: 'BATCH_MODIFY_FIELD_TYPES_PARTIAL_FAILURE',
        failedFields,
        fieldChanges
      };
    }
    
    return { success: true, message: 'BATCH_MODIFY_FIELD_TYPES_SUCCESS', fieldChanges };
  } catch (error) {
    console.error(`批量修改字段类型时发生错误: ${(error as Error).message}`);
    return { success: false, message: 'BATCH_MODIFY_FIELD_TYPES_ERROR' };
  }
}

// 批量隐藏字段
async function batchHideFields(
  sheetId: string,
  viewId: string,
  fieldIds: string[]
): Promise<{ success: boolean; message: string; failedFields?: string[]; successCount?: number }> {
  try {
    const sheet = DingdocsScript.base.getSheet(sheetId);
    if (!sheet) {
      return { success: false, message: 'SHEET_NOT_FOUND' };
    }

    const view = sheet.getView(viewId);
    if (!view) {
      return { success: false, message: 'VIEW_NOT_FOUND' };
    }

    const gridView = view.asGridView()!;

    const failedFields: string[] = [];
    let successCount = 0;

    // 遍历所有需要显示的字段
    for (const fieldId of fieldIds) {
      try {
        // 检查字段是否存在
        const field = sheet.getField(fieldId);
        // @ts-expect-error: isPrimary method may not exist on all field types
        if (!field || (field.isPrimary && field.isPrimary())) {
          failedFields.push(fieldId);
          continue;
        }
        
        // 隐藏字段
        await gridView.hideField(fieldId);
        successCount++;
        console.log(`字段 ${fieldId} 在视图 ${viewId} 中隐藏成功`);
      } catch (error) {
        console.error(`字段 ${fieldId} 在视图 ${viewId} 中隐藏时发生错误: ${(error as Error).message}`);
        failedFields.push(fieldId);
      }
    }
    
    if (failedFields.length > 0) {
      const successFieldsCount = fieldIds.length - failedFields.length;
      return { 
        success: false, 
        message: 'BATCH_HIDE_FIELDS_PARTIAL_FAILURE_WITH_DETAILS',
        failedFields,
        successCount: successFieldsCount
      };
    }

    return { success: true, message: 'BATCH_HIDE_FIELDS_SUCCESS', successCount };
  } catch (error) {
    return { success: false, message: 'BATCH_HIDE_FIELDS_ERROR' };
  }
}

// 批量显示字段
async function batchShowFields(
  sheetId: string,
  viewId: string,
  fieldIds: string[]
): Promise<{ success: boolean; message: string; failedFields?: string[]; successCount?: number }> {
  try {
    const sheet = DingdocsScript.base.getSheet(sheetId);
    if (!sheet) {
      return { success: false, message: 'SHEET_NOT_FOUND' };
    }

    const view = sheet.getView(viewId);
    if (!view) {
      return { success: false, message: 'VIEW_NOT_FOUND' };
    }

    const gridView = view.asGridView()!;

    const failedFields: string[] = [];
    let successCount = 0;
    
    // 遍历所有需要显示的字段
    for (const fieldId of fieldIds) {
      try {
        // 检查字段是否存在
        const field = sheet.getField(fieldId);
        if (!field) {
          failedFields.push(fieldId);
          continue;
        }
        
        // 显示字段
        await gridView.showField(fieldId);
        successCount++;
        console.log(`字段 ${fieldId} 在视图 ${viewId} 中显示成功`);
      } catch (error) {
        console.error(`字段 ${fieldId} 在视图 ${viewId} 中显示时发生错误: ${(error as Error).message}`);
        failedFields.push(fieldId);
      }
    }
    
    if (failedFields.length > 0) {
      const successFieldsCount = fieldIds.length - failedFields.length;
      return { 
        success: false, 
        message: 'BATCH_SHOW_FIELDS_PARTIAL_FAILURE_WITH_DETAILS',
        failedFields,
        successCount: successFieldsCount
      };
    }
    
    return { success: true, message: 'BATCH_SHOW_FIELDS_SUCCESS', successCount };
  } catch (error) {
    return { success: false, message: 'BATCH_SHOW_FIELDS_ERROR' };
  }
}

// 获取当前base的selection
function getBaseSelection() {
  return DingdocsScript.base.getSelection();
}

// 注册服务函数
DingdocsScript.registerScript('getSupportedFieldTypes', getSupportedFieldTypes);
DingdocsScript.registerScript('getSupportedTargetFieldTypes', getSupportedTargetFieldTypes);
DingdocsScript.registerScript('getAllSheets', getAllSheets);
DingdocsScript.registerScript('getSheetFieldsWithDetails', getSheetFieldsWithDetails);
DingdocsScript.registerScript('getGridViewsWithDetails', getGridViewsWithDetails);
DingdocsScript.registerScript('batchModifyFieldTypes', batchModifyFieldTypes);
DingdocsScript.registerScript('batchHideFields', batchHideFields);
DingdocsScript.registerScript('batchShowFields', batchShowFields);
DingdocsScript.registerScript('getBaseSelection', getBaseSelection);

export {};