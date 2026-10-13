# GeoLocationField 地理位置字段

GeoLocationField 继承自基础 [Field](../Field%20模块.md)类，获取地理位置字段的数据。

## 字段特有方法

### getValueAsync

获取指定记录在该字段中的值。

```typescript
getValueAsync: (recordId: string) => Promise<GeoLocationValue | null>

export type GeoLocationValue = {
  /** address */
  address: string;
  /** 简短地址 */
  name: string;
  /** 完整地址 */
  fullAddress: string;
  /** 经纬度 */
  location: [number, number];
};
```

**参数**

*   `recordId`: `string` - 记录ID
    

**返回值**

*   [`Promise<GeoLocationValue | null>`](../../interface/API%20类型定义.md) -  查找到的值，如果没有关联数据则返回null。