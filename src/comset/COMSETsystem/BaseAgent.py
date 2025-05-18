from abc import ABC, abstractmethod
import numpy as np

class BaseAgent(ABC):
    def __init__(self, agent_id, location, simulator):
        self.agent_id = agent_id
        self.location = np.array(location)  # [longitude, latitude]
        self.simulator = simulator
        self.assigned_resource = None
        self.status = "IDLE"  # IDLE, ASSIGNED, MOVING
        
    @abstractmethod
    def assign(self, resource):
        """分配资源给代理"""
        pass
        
    @abstractmethod
    def move(self):
        """移动代理到下一个位置"""
        pass
        
    @abstractmethod
    def update(self):
        """更新代理状态"""
        pass
        
    def get_location(self):
        """获取代理当前位置"""
        return self.location
        
    def get_status(self):
        """获取代理当前状态"""
        return self.status 