// 工具函数

// 本地存储工具
export const storage = {
  get: (key) => {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.error('Error getting from localStorage:', error);
      return null;
    }
  },
  
  set: (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      console.error('Error setting to localStorage:', error);
    }
  },
  
  remove: (key) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  }
};

// 数据转换工具
export const dataUtils = {
  // 更新决策变量
  updateDecisionVar: (key, value) => {
    if (typeof value === "number") {
      const delta = value;
      const increment = {
        transportation_invest: 5,
        agricultural_RnD_cost: 5,
        planting_trees_amount: 100,
        house_migration_amount: 5,
        dam_levee_construction_cost: 1,
        paddy_dam_construction_cost: 5,
        capacity_building_cost: 5,
      }[key] || 1;

      return Math.min(delta * increment, increment * 2);
    }
    return value;
  },

  // 格式化数字
  formatNumber: (num, decimals = 2) => {
    if (typeof num !== 'number') return num;
    return Number(num.toFixed(decimals));
  },

  // 深拷贝对象
  deepClone: (obj) => {
    return JSON.parse(JSON.stringify(obj));
  }
};

// 时间工具
export const timeUtils = {
  // 获取当前时间戳
  getCurrentTimestamp: () => new Date().toISOString(),
  
  // 格式化日期
  formatDate: (date) => {
    return new Date(date).toLocaleDateString();
  }
};

// 验证工具
export const validators = {
  // 验证用户名
  isValidUserName: (name) => {
    return name && name.trim().length > 0;
  },
  
  // 验证数字范围
  isInRange: (value, min, max) => {
    return value >= min && value <= max;
  }
};
