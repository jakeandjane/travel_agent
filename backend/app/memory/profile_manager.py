"""用户偏好档案管理器"""

import json
import os
from pathlib import Path
from .user_profile import UserProfile


class ProfileManager:
    """用户偏好档案管理器（JSON文件持久化）"""

    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            # 默认存储在 backend/data/profiles/
            storage_dir = Path(__file__).parent.parent.parent / "data" / "profiles"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # 内存缓存
        self._cache: dict[str, UserProfile] = {}

    def _file_path(self, user_id: str) -> Path:
        return self.storage_dir / f"{user_id}.json"

    def get_profile(self, user_id: str) -> UserProfile:
        """获取用户档案（优先从缓存，缓存未命中则读文件）"""
        if user_id in self._cache:
            return self._cache[user_id]

        file_path = self._file_path(user_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                profile = UserProfile(**data)
                self._cache[user_id] = profile
                return profile
            except (json.JSONDecodeError, Exception):
                pass

        # 新用户：创建默认档案
        profile = UserProfile(user_id=user_id)
        self._cache[user_id] = profile
        return profile

    def save_profile(self, profile: UserProfile):
        """保存用户档案"""
        self._cache[profile.user_id] = profile
        file_path = self._file_path(profile.user_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)

    def add_visited_city(self, user_id: str, city: str):
        """添加已访问城市"""
        profile = self.get_profile(user_id)
        if city not in profile.visited_cities:
            profile.visited_cities.append(city)
            self.save_profile(profile)

    def update_preferences(self, user_id: str, **kwargs):
        """更新用户偏好"""
        profile = self.get_profile(user_id)
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self.save_profile(profile)


# 全局单例
_profile_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    """获取ProfileManager单例"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
