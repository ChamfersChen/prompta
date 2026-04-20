<template>
  <div class="api-key-management">
    <div class="header-section">
      <div class="header-content">
        <h3 class="title">API Key 管理</h3>
        <p class="description">
          生成第三方访问令牌。密钥明文仅创建时展示一次，请及时保存。可通过
          <code>X-API-Key</code>
          访问开放接口。
        </p>
      </div>
      <a-button type="primary" @click="openCreateModal">
        <template #icon><PlusOutlined /></template>
        创建 API Key
      </a-button>
    </div>

    <div class="content-section">
      <a-spin :spinning="state.loading">
        <div v-if="state.error" class="error-message">
          <a-alert type="error" :message="state.error" show-icon />
        </div>

        <div v-if="state.items.length === 0" class="empty-state">
          <a-empty description="暂无 API Key" />
        </div>

        <a-table
          v-else
          :dataSource="state.items"
          :columns="columns"
          :rowKey="(record) => record.id"
          :pagination="false"
          class="api-key-table"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'key_prefix'">
              <code>{{ record.key_prefix }}</code>
            </template>

            <template v-if="column.key === 'scope'">
              <span v-if="record.user_id">用户 #{{ record.user_id }}</span>
              <span v-else-if="record.department_id">部门 #{{ record.department_id }}</span>
              <span v-else>全局</span>
            </template>

            <template v-if="column.key === 'is_enabled'">
              <a-tag :color="record.is_enabled ? 'green' : 'default'">
                {{ record.is_enabled ? '启用' : '禁用' }}
              </a-tag>
            </template>

            <template v-if="column.key === 'expires_at'">
              {{ formatDateTime(record.expires_at) }}
            </template>

            <template v-if="column.key === 'last_used_at'">
              {{ formatDateTime(record.last_used_at) }}
            </template>

            <template v-if="column.key === 'created_at'">
              {{ formatDateTime(record.created_at) }}
            </template>

            <template v-if="column.key === 'action'">
              <a-space>
                <a-switch
                  :checked="record.is_enabled"
                  checked-children="开"
                  un-checked-children="关"
                  @change="(checked) => toggleEnabled(record, checked)"
                />
                <a-popconfirm
                  title="确认删除该 API Key？"
                  ok-text="删除"
                  cancel-text="取消"
                  @confirm="removeKey(record)"
                >
                  <a-button type="text" danger>
                    <DeleteOutlined />
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-spin>
    </div>

    <a-modal
      v-model:open="state.createVisible"
      title="创建 API Key"
      @ok="submitCreate"
      :confirmLoading="state.creating"
      :maskClosable="false"
      okText="创建"
      cancelText="取消"
    >
      <a-form layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="state.form.name" :maxlength="100" placeholder="例如：第三方系统读取" />
        </a-form-item>

        <a-form-item label="用户名（可选）">
          <a-select
            v-model:value="state.form.username"
            show-search
            allow-clear
            placeholder="默认当前用户"
            :options="state.userOptions.map((user) => ({ label: user.username, value: user.username }))"
            :filter-option="(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())"
          />
        </a-form-item>

        <a-form-item label="部门名称（可选）">
          <a-select
            v-model:value="state.form.department_name"
            show-search
            allow-clear
            placeholder="默认当前部门"
            :options="
              state.departmentOptions.map((department) => ({
                label: department.name,
                value: department.name
              }))
            "
            :filter-option="(input, option) => (option?.label || '').toLowerCase().includes(input.toLowerCase())"
          />
        </a-form-item>

        <a-form-item label="过期时间（可选）">
          <a-date-picker
            v-model:value="state.form.expires_at"
            show-time
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
            placeholder="不填则永不过期"
          />
        </a-form-item>

        <a-form-item label="初始状态">
          <a-switch v-model:checked="state.form.is_enabled" checked-children="启用" un-checked-children="禁用" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="state.plainVisible"
      title="API Key 已创建"
      :footer="null"
      :maskClosable="false"
      @cancel="state.plainVisible = false"
    >
      <p class="plain-tip">请立即复制保存，此密钥不会再次展示：</p>
      <a-input :value="state.plainKey" readonly>
        <template #suffix>
          <a-button type="link" size="small" @click="copyPlainKey">复制</a-button>
        </template>
      </a-input>
      <div class="plain-footer">
        <a-button type="primary" @click="state.plainVisible = false">我已保存</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { Modal, notification } from 'ant-design-vue'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { createApiKey, deleteApiKey, departmentApi, listApiKeys, setApiKeyEnabled } from '@/apis'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/time'

const userStore = useUserStore()

const findUserByName = (username) => state.userOptions.find((user) => user.username === username)
const findDepartmentByName = (departmentName) =>
  state.departmentOptions.find((department) => department.name === departmentName)

const buildDefaultForm = () => ({
  name: '',
  username: userStore.username || '',
  department_name: userStore.departmentName || '',
  expires_at: null,
  is_enabled: true
})

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '前缀', dataIndex: 'key_prefix', key: 'key_prefix', width: 160 },
  { title: '范围', key: 'scope', width: 120 },
  { title: '状态', dataIndex: 'is_enabled', key: 'is_enabled', width: 90 },
  { title: '过期时间', dataIndex: 'expires_at', key: 'expires_at', width: 170 },
  { title: '最后使用', dataIndex: 'last_used_at', key: 'last_used_at', width: 170 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' }
]

const state = reactive({
  loading: false,
  creating: false,
  items: [],
  error: null,
  createVisible: false,
  plainVisible: false,
  plainKey: '',
  userOptions: [],
  departmentOptions: [],
  form: buildDefaultForm()
})

const resetForm = () => {
  state.form = buildDefaultForm()
}

const fetchApiKeys = async () => {
  try {
    state.loading = true
    state.error = null
    const result = await listApiKeys()
    state.items = result?.data || []
  } catch (error) {
    state.error = error.message || '获取 API Key 列表失败'
  } finally {
    state.loading = false
  }
}

const fetchCreateOptions = async () => {
  try {
    const [users, departments] = await Promise.all([
      userStore.getUsers().catch(() => []),
      departmentApi.getDepartments().catch(() => [])
    ])
    state.userOptions = Array.isArray(users) ? users : []
    state.departmentOptions = Array.isArray(departments) ? departments : []
  } catch (error) {
    state.userOptions = []
    state.departmentOptions = []
  }
}

const openCreateModal = () => {
  resetForm()
  state.createVisible = true
}

const submitCreate = async () => {
  if (!state.form.name.trim()) {
    notification.error({ message: '请输入 API Key 名称' })
    return
  }

  const selectedUser = state.form.username ? findUserByName(state.form.username) : null
  const selectedDepartment = state.form.department_name
    ? findDepartmentByName(state.form.department_name)
    : null

  if (state.form.username && !selectedUser) {
    notification.error({ message: '请选择有效的用户名' })
    return
  }

  if (state.form.department_name && !selectedDepartment) {
    notification.error({ message: '请选择有效的部门名称' })
    return
  }

  try {
    state.creating = true
    const payload = {
      name: state.form.name.trim(),
      user_id: selectedUser?.id || null,
      department_id: selectedDepartment?.id || null,
      expires_at: state.form.expires_at || null,
      is_enabled: !!state.form.is_enabled
    }
    const result = await createApiKey(payload)
    state.createVisible = false
    state.plainKey = result?.data?.plain_key || ''
    state.plainVisible = !!state.plainKey
    await fetchApiKeys()
  } catch (error) {
    notification.error({ message: '创建失败', description: error.message || '创建 API Key 失败' })
  } finally {
    state.creating = false
  }
}

const toggleEnabled = async (record, checked) => {
  try {
    await setApiKeyEnabled(record.id, checked)
    record.is_enabled = checked
    notification.success({ message: checked ? '已启用' : '已禁用' })
  } catch (error) {
    notification.error({ message: '更新状态失败', description: error.message || '操作失败' })
  }
}

const removeKey = async (record) => {
  try {
    await deleteApiKey(record.id)
    state.items = state.items.filter((item) => item.id !== record.id)
    notification.success({ message: 'API Key 已删除' })
  } catch (error) {
    notification.error({ message: '删除失败', description: error.message || '删除 API Key 失败' })
  }
}

const copyPlainKey = async () => {
  if (!state.plainKey) return
  try {
    await navigator.clipboard.writeText(state.plainKey)
    notification.success({ message: '已复制到剪贴板' })
  } catch (error) {
    Modal.info({
      title: '复制失败',
      content: '请手动复制当前 API Key。'
    })
  }
}

onMounted(() => {
  fetchCreateOptions()
  fetchApiKeys()
})
</script>

<style lang="less" scoped>
.api-key-management {
  margin-top: 12px;
  min-height: 50vh;

  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;

    .header-content {
      flex: 1;
    }

    .description {
      margin: 0;
      color: var(--gray-600);
      line-height: 1.5;
      font-size: 14px;
    }
  }

  .content-section {
    .error-message {
      margin-bottom: 12px;
    }

    .empty-state {
      padding: 56px 20px;
      text-align: center;
    }
  }

  .api-key-table {
    :deep(.ant-table-thead > tr > th) {
      background: var(--gray-50);
      font-weight: 500;
    }

    code {
      font-family: 'Monaco', 'Consolas', monospace;
      color: var(--gray-800);
    }
  }

  .plain-tip {
    margin-bottom: 10px;
    color: var(--gray-700);
  }

  .plain-footer {
    margin-top: 14px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
