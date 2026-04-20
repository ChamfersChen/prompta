<template>
  <div class="community-row" @click="$emit('click', template)">
    <div class="row-left">
      <div class="row-icon" :style="{ background: getCategoryColor(template.category) }">
        <component :is="getCategoryIcon(template.category)" :size="16" />
      </div>
      <div class="row-info">
        <div class="row-title-line">
          <span class="row-title">{{ template.name }}</span>
          <a-tag color="blue" size="small">提示词</a-tag>
          <a-tag v-if="template.is_official" color="gold" size="small">官方</a-tag>
          <a-tag :color="getCategoryColor(template.category)" size="small">
            {{ getCategoryName(template.category) }}
          </a-tag>
          <span v-if="template.department_name" class="dept-badge">{{ template.department_name }}</span>
        </div>
        <div class="row-description">{{ template.description || '暂无描述' }}</div>
      </div>
    </div>
    <div class="row-right">
      <div class="row-stat">
        <Star :size="13" class="star-icon" />
        <span class="stat-value">{{ template.rating?.toFixed(1) || '0.0' }}</span>
      </div>
      <div class="row-stat">
        <Heart
          :size="13"
          :fill="favorited ? 'currentColor' : 'none'"
          :class="{ favorited_icon: favorited }"
          @click.stop="$emit('favorite', template)"
          style="cursor:pointer"
        />
      </div>
      <div class="row-stat">
        <span>{{ template.favoriteCount || 0 }}</span>
      </div>
      <div class="row-meta">
        <span class="meta-author"><User :size="12" /> {{ template.author || '匿名' }}</span>
        <span class="meta-date">{{ template.created_at }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  Heart, User, Star,
  FileText, Code, BarChart, Globe,
  Briefcase, GraduationCap, Megaphone
} from 'lucide-vue-next'

defineProps({
  template: { type: Object, required: true },
  favorited: { type: Boolean, default: false },
  mode: { type: String, default: 'prompts' }
})

defineEmits(['click', 'favorite', 'fork'])

const getCategoryIcon = (category) => {
  const icons = {
    writing: FileText,
    programming: Code,
    analysis: BarChart,
    translation: Globe,
    office: Briefcase,
    education: GraduationCap,
    marketing: Megaphone
  }
  return icons[category] || FileText
}

const getCategoryColor = (category) => {
  const colors = {
    writing: 'blue', programming: 'green', analysis: 'purple',
    translation: 'orange', office: 'cyan', education: 'gold', marketing: 'red'
  }
  return colors[category] || 'default'
}

const getCategoryName = (category) => {
  const names = {
    writing: '写作', programming: '编程', analysis: '分析',
    translation: '翻译', office: '办公', education: '教育', marketing: '营销'
  }
  return names[category] || category
}
</script>

<style scoped>
.community-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  gap: 16px;
}

.community-row:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.12);
}

.row-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.row-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  margin-top: 2px;
}

.row-info { flex: 1; min-width: 0; }

.row-title-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.row-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.row-description {
  font-size: 12px;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.row-stat {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #666;
}

.stat-value { font-weight: 500; }
.star-icon { color: #faad14; }
.favorited_icon { color: #ff4d4f; }

.row-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.meta-author {
  display: flex;
  align-items: center;
  gap: 3px;
}

.meta-date { white-space: nowrap; }
.dept-badge {
  font-size: 11px;
  background: #e6f7ff;
  color: #1890ff;
  padding: 0 6px;
  border-radius: 3px;
}

:global(.dark) .community-row { background: #1f1f1f; border-color: #303030; }
:global(.dark) .community-row:hover { border-color: #1890ff; }
:global(.dark) .row-title { color: #e5e5e5; }
:global(.dark) .row-description { color: #666; }
:global(.dark) .row-stat { color: #999; }
:global(.dark) .row-meta { color: #666; }
:global(.dark) .dept-badge { background: #111d2c; }
</style>
