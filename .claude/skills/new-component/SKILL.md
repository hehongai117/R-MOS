---
name: new-component
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Generate a new React component following R-MOS frontend architecture conventions.
  This skill creates component scaffolding with proper TypeScript typing, Ant Design
  integration, and project patterns. Use when user requests to create a new UI component.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Write
  - Edit
---

# R-MOS New Component Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **generate scaffolding** for new React components.

It provides:
- Component file generation following project conventions
- TypeScript interface definitions for props
- Ant Design integration patterns
- Proper import structure

### Explicit Non-Goals

This skill MUST NOT:
- Implement complete business logic (only scaffolding)
- Modify existing component files
- Create API services (use backend skills instead)
- Create state management stores
- Create page-level components (use `/new-page` skill if available)
- Add external dependencies or install packages
- Create test files (separate concern)
- Modify global styles or theme configuration

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Framework: `React 18+`
- Language: `TypeScript`
- UI Library: `Ant Design`
- 3D Library: `Three.js / React-Three-Fiber` (for 3D components only)

### Component Categories

| Category | Directory | Description |
|----------|-----------|-------------|
| Common | `src/components/Common/` | Reusable UI components (create if needed) |
| Task | `src/components/Task/` | Task execution related |
| Admin | `src/components/Admin/` | Admin panel components |
| Viewer3D | `src/components/Viewer3D/` | 3D visualization components |

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- React version changes significantly (18 → 19+)
- UI library changes from Ant Design
- TypeScript is replaced
- Component patterns change
- State management approach changes
- Project enters production phase

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Frontend directory `r-mos-frontend/` exists
- Source directory `r-mos-frontend/src/` exists
- Components directory `r-mos-frontend/src/components/` exists
- `r-mos-frontend/package.json` exists (project is initialized)
- Target component file does NOT already exist
- User has provided component name

**Soft Requirements (WARN if fail, continue):**
- Target category directory exists (will create if missing)

❌ If any **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to create a new component
- User enters `/new-component <name>` command
- User mentions "创建新组件" or "create new component"
- User asks to "add a component for..."
- User asks to "create a UI for..."

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify existing component files
- Implement complete business logic (only scaffolding)
- Create API integration code
- Create state management code (hooks/stores)
- Add npm dependencies
- Create test files
- Modify `package.json`
- Create page-level components with routing
- Use non-Ant Design UI components without explicit approval
- Add inline styles beyond basic layout

> 本 skill 禁止任何"顺手帮你修一下"的行为。

---

## 6. Allowed Operations & Tool Constraints

### Tool Usage Rules

- Tools may ONLY be used for purposes explicitly described below.
- All operations must be:
  - Deterministic
  - Single-pass
  - Non-looping

### Tool-Specific Constraints

- **Write**
  - Allowed: Create new component file
  - Allowed: Create category directory (if not exists)
  - Forbidden: Overwrite existing files

- **Edit**
  - Allowed: None for this skill
  - Forbidden: Modifying existing components

- **Read / Grep / Glob**
  - Inspection only
  - Check for existing files and patterns
  - Reference existing components for consistency

- **Bash**
  - Allowed: Check file/directory existence, create directory
  - Forbidden: npm install, file write via echo/cat

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value |
|-----------|-------|
| Frontend Directory | `r-mos-frontend/` |
| Source Directory | `r-mos-frontend/src/` |
| Components Directory | `r-mos-frontend/src/components/` |
| Framework | React 18+ |
| Language | TypeScript (.tsx) |
| UI Library | Ant Design |
| Import Alias | `@/` → `src/` (if configured in tsconfig.json) |

### Existing Component Patterns

| Component | File | Key Features |
|-----------|------|--------------|
| StepCard | `Task/StepCard.tsx` | Props interface, Ant Design Card, conditional rendering |
| RobotModel | `Viewer3D/RobotModel.tsx` | Three.js Canvas, React-Three-Fiber |
| SeedDataGuide | `Admin/SeedDataGuide.tsx` | Named export, Ant Design Alert/Typography |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Component File Contract

All components MUST follow this structure:

```tsx
/**
 * <ComponentName>组件
 *
 * 描述: <brief description>
 */
import React from 'react';
// Ant Design imports
// Local imports

interface <ComponentName>Props {
  // Props definition with JSDoc comments
}

const <ComponentName>: React.FC<<ComponentName>Props> = ({ /* props */ }) => {
  return (
    // JSX
  );
};

export default <ComponentName>;
```

### Props Interface Contract

All props interfaces MUST:
- Use `interface` (not `type`)
- End with `Props` suffix
- Include JSDoc comments for complex props
- Use proper TypeScript types (no `any` without justification)

### Export Contract

| Component Type | Export Pattern |
|----------------|----------------|
| Default (most cases) | `export default ComponentName;` |
| Named (reusable utility) | `export const ComponentName: React.FC = ...` |

❌ Any deviation → **WARN and suggest correction**

---

## 9. Execution Plan（固定流程，不可跳步）

### Placeholder Convention

In all templates below:
- `<name>` → lowercase component name (e.g., `status_panel`)
- `<Name>` → PascalCase component name (e.g., `StatusPanel`)
- `<Category>` → Component category (Common, Task, Admin, Viewer3D)

These placeholders MUST be replaced with actual values during generation.

---

### Step 1 — Validate Input

* Action: Confirm component name and category
* Checks:
  - Component name provided by user
  - Name follows PascalCase convention
  - Category specified (default: Common)
  - package.json exists
  - Target file does not exist
* Command:
  ```bash
  cd r-mos-frontend
  echo "=== Checking Prerequisites ==="
  [ -f "package.json" ] && echo "✓ package.json exists" || echo "✗ package.json not found - project not initialized"
  [ -d "src/components" ] && echo "✓ components directory exists" || echo "✗ components directory not found"
  [ -f "src/components/<Category>/<Name>.tsx" ] && echo "✗ Component file already exists" || echo "✓ Component file does not exist"
  ```
* Failure condition: package.json not found OR file already exists OR name not provided

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Create Category Directory (If Needed)

* Action: Ensure category directory exists
* Command:
  ```bash
  cd r-mos-frontend
  mkdir -p src/components/<Category>
  echo "✓ Category directory ready: src/components/<Category>/"
  ```
* Expected result: Directory exists or created
* Failure condition: None

---

### Step 3 — Reference Existing Patterns

* Action: Read existing component for consistency
* Command:
  ```bash
  cd r-mos-frontend
  head -40 src/components/Task/StepCard.tsx 2>/dev/null || echo "No reference component found"
  ```
* Purpose: Ensure generated code follows same patterns
* Failure condition: None

---

### Step 4 — Generate Component File

* Action: Create new component file with scaffolding
* File: `r-mos-frontend/src/components/<Category>/<Name>.tsx`
* Template: See §9.4 Template below
* Failure condition: Write operation fails

---

### Step 5 — Verify Generation

* Action: Confirm file was created correctly
* Command:
  ```bash
  cd r-mos-frontend
  ls -la src/components/<Category>/<Name>.tsx
  head -30 src/components/<Category>/<Name>.tsx
  ```
* Failure condition: File not found or malformed

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

### 9.4 Component File Template

#### Standard Component (Ant Design)

```tsx
/**
 * <Name>组件
 *
 * 描述: TODO - Add component description
 */
import React from 'react';
import { Card, Space } from 'antd';

/**
 * <Name>组件属性
 */
interface <Name>Props {
  /** TODO: Add prop description */
}

/**
 * <Name>组件
 *
 * TODO: Add detailed component description
 */
const <Name>: React.FC<<Name>Props> = ({
  // TODO: Destructure props
}) => {
  return (
    <Card title="<Name>">
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* TODO: Add component content */}
        <div>Component content goes here</div>
      </Space>
    </Card>
  );
};

export default <Name>;
```

#### 3D Component Template (Viewer3D category)

```tsx
/**
 * <Name> 3D组件
 *
 * 描述: TODO - Add component description
 */
import React, { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

/**
 * <Name>组件属性
 */
interface <Name>Props {
  /** TODO: Add prop description */
}

/**
 * 内部3D场景组件
 */
const Scene: React.FC = () => {
  const meshRef = useRef<THREE.Mesh>(null);

  return (
    <mesh ref={meshRef}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#1890ff" />
    </mesh>
  );
};

/**
 * <Name>组件
 *
 * TODO: Add detailed component description
 */
const <Name>: React.FC<<Name>Props> = ({
  // TODO: Destructure props
}) => {
  return (
    <Canvas camera={{ position: [5, 5, 5], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      <Scene />
      <OrbitControls />
    </Canvas>
  );
};

export default <Name>;
```

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Component name not provided
* Target file already exists
* Components directory not found
* Write operation fails

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: New Component Generation

Generated Files:
  - src/components/<Category>/<Name>.tsx: CREATED | FAILED

Component Details:
  Name: <Name>
  Category: <Category>
  Type: Standard | 3D
  Export: default | named

Usage Example:
  // If @/ alias configured:
  import <Name> from '@/components/<Category>/<Name>';
  // Or use relative path:
  import <Name> from '../components/<Category>/<Name>';

  // In your component:
  <<Name> />

Next Recommended Action:
  - Add props to the Props interface
  - Implement component logic
  - Import and use in parent component
```

---

## 11. Related Files / Interfaces（只读参考）

* `r-mos-frontend/src/components/Task/StepCard.tsx` — Standard component reference
* `r-mos-frontend/src/components/Viewer3D/RobotModel.tsx` — 3D component reference
* `r-mos-frontend/src/components/Admin/SeedDataGuide.tsx` — Named export reference
* `r-mos-frontend/src/types/` — Type definitions (if exists)
* `r-mos-frontend/src/hooks/` — Custom hooks (if exists)

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* React version changes significantly
* UI library changes from Ant Design
* TypeScript is replaced or version changes significantly
* Component patterns or directory structure changes
* Import alias convention changes
* Project enters production phase with different patterns

Once invalid, this skill MUST NOT be executed without human review.

---
