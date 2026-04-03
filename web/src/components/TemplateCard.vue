<template>
  <div class="template-card" @click="$emit('click', template)">
    <div class="card-header">
      <div class="card-icon" :style="{ background: getCategoryColor(template.category) }">
        <component :is="getCategoryIcon(template.category)" :size="18" />
      </div>
      <div class="card-actions">
        <a-button
          v-if="mode !== 'mine'"
          type="text"
          size="small"
          @click.stop="$emit('favorite', template)"
          :class="{ favorited: favorited }"
        >
          <Heart :size="14" :fill="favorited ? 'currentColor' : 'none'" />
        </a-button>
        <a-tag v-else-if="template.is_official" color="gold" size="small">官方</a-tag>
        <a-tag v-else-if="template.is_public" color="blue" size="small">公开</a-tag>
        <a-tag v-else color="default" size="small">私有</a-tag>
      </div>
    </div>

    <div class="card-body">
      <h3 class="card-title">{{ template.name }}</h3>
      <p class="card-description">{{ template.description || '暂无描述' }}</p>
      <div class="card-tags" v-if="template.tags?.length">
        <a-tag v-for="tag in template.tags.slice(0, 3)" :key="tag" size="small">
          {{ tag }}
        </a-tag>
      </div>
    </div>

    <div class="card-footer">
      <div class="card-meta">
        <span class="author">
          <User :size="12" />
          {{ template.author || '匿名' }}
        </span>
        <a-tag :color="getCategoryColor(template.category)" size="small">
          {{ getCategoryName(template.category) }}
        </a-tag>
      </div>
      <div class="card-rating">
        <Star :size="12" class="star-icon" />
        <span>{{ template.rating?.toFixed(1) || '0.0' }}</span>
        <span class="rating-count">({{ template.ratingCount || 0 }})</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  Heart,
  User,
  Play,
  Star,
  FileText,
  Code,
  BarChart,
  Globe,
  Briefcase,
  GraduationCap,
  Megaphone
} from 'lucide-vue-next'

defineProps({
  template: {
    type: Object,
    required: true
  },
  favorited: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'official'
  }
})

defineEmits(['click', 'favorite', 'fork', 'use'])

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
    writing: 'blue',
    programming: 'green',
    analysis: 'purple',
    translation: 'orange',
    office: 'cyan',
    education: 'gold',
    marketing: 'red'
  }
  return colors[category] || 'default'
}

const getCategoryName = (category) => {
  const names = {
    writing: '写作',
    programming: '编程',
    analysis: '分析',
    translation: '翻译',
    office: '办公',
    education: '教育',
    marketing: '营销'
  }
  return names[category] || category
}
</script>

<style scoped>
.template-card {
  position: relative;
  width: 260px;
  height: 180px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.template-card:hover {
  border-color: #1890ff;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.15);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.card-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.card-actions .ant-btn {
  padding: 4px;
}

.card-actions .favorited {
  color: #ff4d4f;
}

.card-body {
  flex: 1;
  min-height: 0;
  margin-bottom: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 6px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-description {
  font-size: 12px;
  color: #666;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
  height: 36px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.card-meta {
  display: flex;
  gap: 6px;
  align-items: center;
}

.card-meta span {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #999;
}

.card-rating {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #666;
}

.star-icon {
  color: #faad14;
}
</style>
