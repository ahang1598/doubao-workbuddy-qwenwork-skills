# AI Table Sidebar Plugin Generator Skill

This Skill helps Claude generate production-ready AI Table (DingTalk Table) sidebar plugins.

## Features

- ✅ **Strict API Compliance**: Only uses APIs defined in `./references` and `../shared/references`
- ✅ **Production Ready**: Complete error handling and user feedback
- ✅ **Dual-Page Architecture**: Auto-generates Service page (Web Worker) and UI page (Sidebar)
- ✅ **Type Safety**: TypeScript development with full type support
- ✅ **React Framework**: Built with React for user interface
- ✅ **Event Listening**: Supports event monitoring (button clicks, selection changes, etc.)
- ✅ **Complete Output**: Generates service.ts, ui.tsx, script.tsx and related configuration files

## Usage

### In Claude.ai

1. Upload the `.skills/ai-sidebar-plugin` folder to Claude.ai Skills settings
2. Enable the Skill
3. Describe your requirements in natural language, for example:

```
Create a sidebar plugin that displays the record count of the current data table
```

```
Generate a sidebar plugin that can batch update the status of selected records
```

```
Write a sidebar plugin that automatically fills in data when a button field is clicked
```

### In Claude Code

1. Copy the `.skills/ai-sidebar-plugin` folder to the project's `skills/` directory
2. Claude Code will automatically load the Skill
3. State your requirements directly in the conversation

## Architecture Overview

Sidebar plugins use a dual-page architecture:

- **Script Service Page**: Runs in Web Worker, responsible for interacting with AI Table data model
- **UI Interaction Page**: Runs in sidebar iframe, responsible for user interface display and interaction

## Generated Output

The Skill generates the following based on your requirements:

### 1. Service Page (service.ts)
Contains:
- Data operation function definitions
- Script service instruction registration (using `DingdocsScript.registerScript`)
- Access AI Table data model through `DingdocsScript.base`

### 2. Script Entry Page (script.tsx)
Contains:
- Initialize document model service using `initScript`
- Load bundled service.ts script file

### 3. UI Entry Page (ui.tsx)
Contains:
- Initialize sidebar interaction page using `initView`
- React component definitions
- Execute script service instructions by calling `Dingdocs.script.run`
- Event listener registration (e.g., `Dingdocs.base.event.onButtonFieldClicked`)

## Supported Features

### Data Reading
- Read currently active table, view, fields
- Read record data
- Read field values

### Data Operations
- Insert new records
- Update records
- Delete records
- Batch operations

### Event Listening
- Button field click events
- Selection area change events
- Record insert/modify/delete events
- Field insert/modify/delete events

### User Interaction
- Form input
- Selectors
- Text input
- Real-time feedback

## Common Operation Examples

### Display Data Table Information
```
Create a sidebar plugin that displays basic information about the current data table
```

### Batch Update Data
```
Create a sidebar plugin that can batch set all records' status to "Completed"
```

### Button-Triggered Operations
```
Create a sidebar plugin that automatically fills in the current record's creation time when a button field is clicked
```

### Data Statistics
```
Create a sidebar plugin that counts the number of records for each status in the current data table
```

## API Usage Guidelines

### Service Page APIs

Use the following APIs in service.ts:

```typescript
// Access AI Table model
const base = DingdocsScript.base;

// Get currently active data table
const sheet = base.getActiveSheet();

// Register script service instruction
DingdocsScript.registerScript('functionName', myFunction);
```

### UI Page APIs

Use the following APIs in ui.tsx:

```typescript
// Initialize sidebar
initView({
  onReady: () => { /* Initialization logic */ },
  onError: (e) => { /* Error handling */ },
});

// Execute script service instruction
const result = await Dingdocs.script.run('functionName');

// Listen to events
Dingdocs.base.event.onButtonFieldClicked((event) => {
  // Handle button click event
});
```

### Data Model APIs

Refer to documents in `../shared/references/api/` directory:

- **Base Module**: AI Table top-level object
- **Sheet Module**: Data table operations
- **Field Module**: Field operations
- **Record Module**: Record operations
- **View Module**: View operations
- **Input Module**: User input
- **Output Module**: Output information
- **UI Module**: UI interaction

## Code Quality Assurance

Generated code follows these principles:

1. **API Compliance**: Only uses API methods defined in documentation
2. **Error Handling**: All operations include error handling logic
3. **User Feedback**: Uses UI module to provide user feedback
4. **Type Safety**: Uses TypeScript type definitions
5. **Event Handling**: Properly registers and cleans up event listeners
6. **Clear Comments**: Key logic includes explanatory comments

## Important Notes

1. **Do Not Invent APIs**: Skill strictly follows API definitions in documentation and won't create any methods
2. **Dual-Page Separation**: Service page handles data operations, UI page handles user interaction
3. **Event Listening**: Remember to clean up event listeners when component unmounts
4. **Async Operations**: All data operations are asynchronous, use await to handle them
5. **Permission Check**: Ensure users have appropriate permissions to perform operations

## Reference Documentation

The Skill includes the following reference documents:

- `references/AI表格边栏插件 开发指南.md` - Sidebar plugin development guide
- `references/Event事件模块.md` - Event monitoring documentation
- `references/核心知识.md` - Core concepts
- `references/其他接口.md` - Other available interfaces

Shared API documentation is located in `../shared/references/api/` directory.

## Example Conversations

### User: Create a sidebar plugin that displays the record count of the current data table

**Claude will generate:**

1. **service.ts** - Script service for getting record count
2. **script.tsx** - Entry point for initializing script service
3. **ui.tsx** - UI interface that displays record count

The generated plugin will:
- Define a function to get record count in service.ts
- Display the current data table's record count in ui.tsx
- Provide a refresh button to update data in real-time

### User: Create a sidebar plugin that automatically fills in the current record's creation time when a button field is clicked

**Claude will generate:**

1. **service.ts** - Script service for filling creation time
2. **script.tsx** - Entry point for initializing script service
3. **ui.tsx** - UI interface with event listening

The generated plugin will:
- Define a function to fill creation time in service.ts
- Listen to button field click events in ui.tsx
- Automatically get current record and fill creation time
- Provide operation feedback

## Publishing Related

When users mention publishing, provide the following guidance:

- Enterprise plugin publishing guide (in `references/AI 表格插件 - 企业内插件发布指南.md`)
- Plugin authentication instructions
- Cool app creation process
- Publishing steps

## Version Information

- Version: 1.0.0
- Author: AI Table Team
- License: MIT