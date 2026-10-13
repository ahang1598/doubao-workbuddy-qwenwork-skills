# Example Scripts

## 1. Email Validation Script

Complete example of a validation script that creates a result field and validates email addresses.

```typescript
async function main() {
  try {
    // Step 1: Collect user input
    const formResult = await Input.formAsync('邮箱验证配置', [
      {
        type: 'sheet',
        key: 'sheet',
        option: {
          label: '选择数据表'
        },
        required: true
      },
      {
        type: 'field',
        key: 'emailField',
        option: {
          label: '选择邮箱字段',
          referenceSheet: 'sheet'
        },
        required: true
      }
    ]);

    const sheet = formResult.sheet;
    const emailField = formResult.emailField;
    const fieldName = emailField.getName();

    // Step 2: Check or create validation result field
    let validationField = sheet.getField('邮箱验证结果');
    let validationFieldId;
    
    if (validationField) {
      const overwrite = await Input.selectAsync('字段"邮箱验证结果"已存在，是否覆盖该字段的值?', ['是', '否']);
      if (overwrite === '否') {
        Output.log('用户取消操作');
        return;
      }
      validationFieldId = validationField.getId();
    } else {
      validationField = sheet.insertField('邮箱验证结果', 'text');
      validationFieldId = validationField.getId();
    }

    // Step 3: Define validation regex
    const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$/;

    // Step 4: Load all records
    const result = await sheet.getRecordsAsync({
      pageSize: 500,
    });

    // Step 5: Process each record
    const updates = [];

    for (const record of result.records) {
      const cellValue = record.getCellValue(fieldName);
      
      // Only process string values
      if (typeof cellValue !== "string") {
        updates.push({
          id: record.getId(),
          fields: {
            [validationFieldId]: '无效（非文本）'
          }
        });
        continue;
      }

      let isValid = false;
      if (cellValue) {
        const validation = cellValue.match(emailRegex);
        isValid = validation !== null;
      }

      updates.push({
        id: record.getId(),
        fields: {
          [validationFieldId]: isValid ? '有效' : '无效'
        }
      });
    }

    // Step 6: Batch update records
    const maxRecordsPerCall = 500;
    while (updates.length > 0) {
      const batch = updates.slice(0, maxRecordsPerCall);
      await sheet.updateRecordsAsync(batch);
      updates.splice(0, maxRecordsPerCall);
    }

    Output.log(`邮箱验证完成，结果生成在「邮箱验证结果」字段中。共处理了 ${result.records.length} 条记录。`);
  } catch (error) {
    if (error instanceof Error) {
      Output.error(`执行过程中发生错误: ${error.message}`);
    } else {
      Output.error(`执行过程中发生未知错误`);
    }
  }
}

await main();
```

## 2. Find and Replace Script

Example of text search and replace functionality.

```typescript
async function main() {
  try {
    let currentSheet = Base.getActiveSheet();
    
    const formResult = await Input.formAsync('查找和替换配置', [
      {
        type: 'sheet',
        key: 'sheet',
        option: {
          label: '数据表',
          description: '请选择要操作的数据表'
        },
        required: !currentSheet
      },
      {
        type: 'field',
        key: 'field',
        option: {
          label: '字段',
          description: '请选择要进行查找替换的文本字段',
          referenceSheet: 'sheet'
        },
        required: true
      },
      {
        type: 'text',
        key: 'findText',
        option: {
          label: '查找文本',
          description: '请输入要查找的文本内容'
        },
        required: true
      },
      {
        type: 'text',
        key: 'replaceText',
        option: {
          label: '替换文本',
          description: '请输入要替换的文本内容（留空则删除查找到的文本）'
        },
        required: false
      }
    ]);

    if (formResult.sheet) {
      currentSheet = formResult.sheet;
    }
    
    if (!currentSheet) {
      Output.error('请先激活一个数据表或选择数据表');
      return;
    }

    const currentField = formResult.field;

    if (currentField.getType() !== 'text') {
      Output.error('只能对文本字段进行查找替换操作');
      return;
    }

    const findText = formResult.findText;
    const replaceText = formResult.replaceText || '';

    Output.log(`准备在数据表 "${currentSheet.getName()}" 的字段 "${currentField.getName()}" 中查找 "${findText}" 并替换为 "${replaceText}"`);

    // Load all records
    const allRecords = [];
    let hasMore = true;
    let cursor = "";

    while (hasMore) {
      const result = await currentSheet.getRecordsAsync({
        pageSize: 500,
        cursor: cursor,
      });

      allRecords.push(...result.records);
      hasMore = result.hasMore;
      cursor = result.cursor;
    }

    // Find replacements
    const replacements = [];

    for (const record of allRecords) {
      const originalValue = record.getCellValue(currentField.getName());

      if (typeof originalValue !== 'string') {
        continue;
      }

      if (!originalValue) {
        continue;
      }

      // Replace text with proper regex escaping
      const newValue = originalValue.replace(new RegExp(findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), replaceText);

      if (originalValue !== newValue) {
        replacements.push({
          recordId: record.getId(),
          before: originalValue,
          after: newValue,
        });
      }
    }

    if (replacements.length === 0) {
      Output.log('未找到需要替换的内容');
    } else {
      Output.log(`找到 ${replacements.length} 处需要替换的内容:`);
      
      const displayLimit = 10;
      for (let i = 0; i < Math.min(replacements.length, displayLimit); i++) {
        const replacement = replacements[i];
        Output.log(`记录 ${replacement.recordId}: "${replacement.before}" -> "${replacement.after}"`);
      }
      
      if (replacements.length > displayLimit) {
        Output.log(`...还有 ${replacements.length - displayLimit} 项`);
      }
      
      const confirm = await Input.selectAsync('是否确认执行替换操作?', ['是', '否']);
      
      if (confirm === '是') {
        const updates = replacements.map((replacement) => ({
          id: replacement.recordId,
          fields: {
            [currentField.getName()]: replacement.after,
          },
        }));
        
        const batchSize = 500;
        while (updates.length > 0) {
          const batch = updates.slice(0, batchSize);
          await currentSheet.updateRecordsAsync(batch);
          updates.splice(0, batchSize);
        }
        
        Output.log(`成功替换 ${replacements.length} 条记录`);
      } else {
        Output.log('已取消替换操作');
      }
    }
  } catch (error) {
    Output.error(`执行过程中发生错误: ${error.message}`);
  }
}

await main();
```

## 3. Random Value Generation Script

Example of filling fields with random values for testing.

```typescript
async function main() {
  try {
    let currentSheet = Base.getActiveSheet();

    if (!currentSheet) {
      const sheetName = await Input.textAsync('请输入数据表名称:');
      const sheet = Base.getSheet(sheetName);
      
      if (!sheet) {
        Output.error('未找到指定的数据表');
        return;
      }
      
      currentSheet = sheet;
    } else {
      Output.log(`当前数据表: ${currentSheet.getName()}`);
    }

    const fieldName = await Input.textAsync('请选择要随机填充的字段名称:');

    const currentField = currentSheet.getField(fieldName);

    if (!currentField) {
      Output.error(`未找到字段: ${fieldName}`);
      return;
    }

    const supportedTypes = ['number', 'currency', 'date', 'singleSelect', 'multipleSelect'];
    if (!supportedTypes.includes(currentField.getType())) {
      Output.error(`字段类型 '${currentField.getType()}' 不支持随机填充。支持的类型: ${supportedTypes.join(', ')}`);
      return;
    }

    Output.log(`准备随机填充数据表 "${currentSheet.getName()}" 中的字段 "${currentField.getName()}"`);

    switch (currentField.getType()) {
      case 'number': {
        const min = await Input.textAsync('请输入最小值:');
        const max = await Input.textAsync('请输入最大值:');
        await randomizeNumberField(currentSheet, currentField, Number(min), Number(max));
        break;
      }
      case 'currency': {
        const min = await Input.textAsync('请输入最小值:');
        const max = await Input.textAsync('请输入最大值:');
        await randomizeCurrencyField(currentSheet, currentField, Number(min), Number(max));
        break;
      }
      case 'date': {
        const min = await Input.textAsync('请输入最早日期 (YYYY-MM-DD):');
        const max = await Input.textAsync('请输入最晚日期 (YYYY-MM-DD):');
        await randomizeDateField(currentSheet, currentField, new Date(min), new Date(max));
        break;
      }
      case 'singleSelect': {
        await randomizeSingleSelectField(currentSheet, currentField);
        break;
      }
      case 'multipleSelect': {
        const min = await Input.textAsync('请输入最少选择项数量:');
        const max = await Input.textAsync('请输入最多选择项数量:');
        await randomizeMultipleSelectField(currentSheet, currentField, Number(min), Number(max));
        break;
      }
      default: {
        Output.error(`不支持的字段类型: ${currentField.getType()}`);
        return;
      }
    }
  } catch (error) {
    Output.error(`执行过程中发生错误: ${error.message}`);
  }
}

async function randomizeNumberField(sheet, field, min, max) {
  const allRecords = await loadAllRecords(sheet);
  const updates = [];
  
  for (const record of allRecords) {
    const randomValue = Math.random() * (max - min) + min;
    updates.push({
      id: record.getId(),
      fields: {
        [field.getName()]: randomValue
      }
    });
  }
  
  await updateRecordsInBatches(sheet, updates);
  Output.log(`成功随机填充 ${allRecords.length} 条记录的数字字段`);
}

async function randomizeCurrencyField(sheet, field, min, max) {
  const allRecords = await loadAllRecords(sheet);
  const updates = [];
  
  for (const record of allRecords) {
    const randomValue = Math.random() * (max - min) + min;
    updates.push({
      id: record.getId(),
      fields: {
        [field.getName()]: randomValue
      }
    });
  }
  
  await updateRecordsInBatches(sheet, updates);
  Output.log(`成功随机填充 ${allRecords.length} 条记录的货币字段`);
}

async function randomizeDateField(sheet, field, minDate, maxDate) {
  const allRecords = await loadAllRecords(sheet);
  const updates = [];
  const minTime = minDate.getTime();
  const maxTime = maxDate.getTime();
  
  for (const record of allRecords) {
    const randomTime = Math.random() * (maxTime - minTime) + minTime;
    const randomDate = new Date(randomTime);
    updates.push({
      id: record.getId(),
      fields: {
        [field.getName()]: randomDate.getTime()
      }
    });
  }
  
  await updateRecordsInBatches(sheet, updates);
  Output.log(`成功随机填充 ${allRecords.length} 条记录的日期字段`);
}

async function randomizeSingleSelectField(sheet, field) {
  const selectField = sheet.getField(field.getName());
  
  if (!selectField) {
    Output.error('无法获取单选字段');
    return;
  }
  
  const options = selectField.getOptions();
  
  if (!options || options.length === 0) {
    Output.error('单选字段没有选项');
    return;
  }
  
  const allRecords = await loadAllRecords(sheet);
  const updates = [];
  
  for (const record of allRecords) {
    const randomIndex = Math.floor(Math.random() * options.length);
    const randomOption = options[randomIndex];
    updates.push({
      id: record.getId(),
      fields: {
        [field.getName()]: randomOption.id
      }
    });
  }
  
  await updateRecordsInBatches(sheet, updates);
  Output.log(`成功随机填充 ${allRecords.length} 条记录的单选字段`);
}

async function randomizeMultipleSelectField(sheet, field, min, max) {
  const selectField = sheet.getField(field.getName());
  
  if (!selectField) {
    Output.error('无法获取多选字段');
    return;
  }
  
  const options = selectField.getOptions();
  
  if (!options || options.length === 0) {
    Output.error('多选字段没有选项');
    return;
  }
  
  const allRecords = await loadAllRecords(sheet);
  const updates = [];
  
  for (const record of allRecords) {
    const numSelections = Math.floor(Math.random() * (max - min + 1)) + min;
    const shuffledOptions = [...options].sort(() => 0.5 - Math.random());
    const selectedOptions = shuffledOptions.slice(0, numSelections);
    
    updates.push({
      id: record.getId(),
      fields: {
        [field.getName()]: selectedOptions.map((option) => option.id)
      }
    });
  }
  
  await updateRecordsInBatches(sheet, updates);
  Output.log(`成功随机化填充 ${allRecords.length} 条记录的多选字段`);
}

async function loadAllRecords(sheet) {
  const allRecords = [];
  let hasMore = true;
  let cursor = "";

  while (hasMore) {
    const result = await sheet.getRecordsAsync({
      pageSize: 500,
      cursor: cursor,
    });

    allRecords.push(...result.records);
    hasMore = result.hasMore;
    cursor = result.cursor;
  }
  
  return allRecords;
}

async function updateRecordsInBatches(sheet, updates) {
  const batchSize = 500;
  while (updates.length > 0) {
    const batch = updates.slice(0, batchSize);
    await sheet.updateRecordsAsync(batch);
    updates.splice(0, batchSize);
  }
}

await main();
```

## 4. Mark Duplicates Script

Example of identifying and marking duplicate records.

```typescript
async function main() {
  try {
    const formResult = await Input.formAsync('标记重复记录配置', [
      {
        type: 'sheet',
        key: 'sheet',
        option: {
          label: '数据表',
          description: '请选择要操作的数据表'
        },
        required: true
      },
      {
        type: 'text',
        key: 'idFieldsInput',
        option: {
          label: '标识字段',
          description: '请输入标识字段（多个字段用逗号分隔）'
        },
        required: true
      },
      {
        type: 'select',
        key: 'markType',
        option: {
          label: '标记方式',
          description: '请选择重复记录的标记方式',
          options: ['标记全部', '首项不标记', '末项不标记']
        },
        required: true
      },
      {
        type: 'field',
        key: 'comparisonField',
        option: {
          label: '比较字段',
          description: '请选择用于排序的比较字段（标记全部时可不选）',
          referenceSheet: 'sheet'
        },
        required: false
      }
    ]);
    
    const sheet = formResult.sheet;
    const idFieldsInput = formResult.idFieldsInput;
    const idFields = idFieldsInput.split(/,|，/g).map(field => field.trim());
    const markType = formResult.markType;
    const comparisonField = formResult.comparisonField;
    
    // Validate fields exist
    const sheetFields = sheet.getFields();
    const fieldNames = sheetFields.map(field => field.getName());
    const fieldIds = sheetFields.map(field => field.getId());
    const validFields = [...fieldNames, ...fieldIds];
    
    const invalidFields = idFields.filter(field => !validFields.includes(field));
    if (invalidFields.length > 0) {
      Output.error(`以下标识字段不存在: ${invalidFields.join(', ')}`);
      return;
    }
    
    if (markType !== '标记全部' && !comparisonField) {
      Output.error('当标记方式为"首项不标记"或"末项不标记"时，比较字段是必填项');
      return;
    }
    
    const maxRecordsPerCall = 500;
    
    // Check or create duplicate flag field
    let duplicateFlagField = sheet.getField('标记重复值');
    let duplicateFlagFieldId;
    
    if (duplicateFlagField) {
      const overwrite = await Input.selectAsync('字段"标记重复值"已存在，是否覆盖该字段值?', ['是', '否']);
      if (overwrite === '否') {
        Output.log('用户取消操作');
        return;
      }
      duplicateFlagFieldId = duplicateFlagField.getId();
    } else {
      duplicateFlagField = sheet.insertField('标记重复值', 'text');
      duplicateFlagFieldId = duplicateFlagField.getId();
    }
    
    // Load all records (max 20000)
    const allRecords = [];
    let hasMore = true;
    let cursor = "";
    const maxRecords = 20000;

    while (hasMore && allRecords.length < maxRecords) {
      const result = await sheet.getRecordsAsync({
        pageSize: 500,
        cursor: cursor,
      });

      const remainingSpace = maxRecords - allRecords.length;
      if (result.records.length > remainingSpace) {
        allRecords.push(...result.records.slice(0, remainingSpace));
        hasMore = false;
      } else {
        allRecords.push(...result.records);
        hasMore = result.hasMore;
        cursor = result.cursor;
      }
    }

    if (!hasMore && allRecords.length === maxRecords) {
      Output.log(`注意：表格记录数超过${maxRecords}条，仅处理前${maxRecords}条记录。`);
    }
    
    const updates = [];
    
    // Group records by identifier fields
    const groups = {};
    for (const record of allRecords) {
      const key = JSON.stringify(
        idFields.map(field => record.getCellValue(field))
      );
      
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(record);
    }
    
    // Process each group
    for (const [, records] of Object.entries(groups)) {
      if (records.length === 1) {
        updates.push({
          id: records[0].getId(),
          fields: {
            [duplicateFlagFieldId]: ''
          }
        });
      } else {
        let recordsToMark = [...records];
        
        if (markType === '首项不标记') {
          if (comparisonField) {
            recordsToMark.sort((a, b) => {
              const valueA = a.getCellValue(comparisonField.getName());
              const valueB = b.getCellValue(comparisonField.getName());
              if (valueA < valueB) return -1;
              if (valueA > valueB) return 1;
              return 0;
            });
          }
          recordsToMark = recordsToMark.slice(1);
        } else if (markType === '末项不标记') {
          if (comparisonField) {
            recordsToMark.sort((a, b) => {
              const valueA = a.getCellValue(comparisonField.getName());
              const valueB = b.getCellValue(comparisonField.getName());
              if (valueA < valueB) return -1;
              if (valueA > valueB) return 1;
              return 0;
            });
          }
          recordsToMark = recordsToMark.slice(0, -1);
        }
        
        for (const record of recordsToMark) {
          updates.push({
            id: record.getId(),
            fields: {
              [duplicateFlagFieldId]: '重复项'
            }
          });
        }
        
        const unmarkedRecords = records.filter(record => !recordsToMark.includes(record));
        for (const record of unmarkedRecords) {
          updates.push({
            id: record.getId(),
            fields: {
              [duplicateFlagFieldId]: ''
            }
          });
        }
      }
    }
    
    // Update records
    while (updates.length > 0) {
      const batch = updates.slice(0, maxRecordsPerCall);
      await sheet.updateRecordsAsync(batch);
      updates.splice(0, maxRecordsPerCall);
    }
    
    Output.log(`标记方式 ${markType} 共处理了 ${allRecords.length} 条记录。`);
  } catch (error) {
    if (error instanceof Error) {
      Output.error(`执行过程中发生错误: ${error.message}`);
    } else {
      Output.error(`执行过程中发生未知错误`);
    }
  }
}

await main();
```

## Key Takeaways

1. **Always use try-catch** for error handling
2. **Use Input.formAsync** for complex configurations
3. **Process in batches**（脚本/边栏插件上限：insert 1000 / update 500 / delete 500 / getRecordsAsync pageSize 500）
4. **Validate field types** before operations
5. **Provide user feedback** via Output methods
6. **Load all records** with pagination pattern
7. **Match value types** to field type requirements
8. **Use Base.isFieldOfType()** for type safety