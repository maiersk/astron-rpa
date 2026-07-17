<script setup lang="ts">
import { PlusOutlined, DeleteOutlined, EditOutlined, ApiOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import { message, Button, Table, Tag, Tooltip, Popconfirm, Space, Empty } from 'ant-design-vue'
import { useTranslation } from 'i18next-vue'
import { h, onMounted, ref } from 'vue'

import { deleteProvider, getProviders, testProvider } from '@/api/aiProvider'
import type { ProviderResponse } from '@/api/aiProvider'

import ProviderFormModal from './ProviderFormModal.vue'

const { t } = useTranslation()

const loading = ref(false)
const providers = ref<ProviderResponse[]>([])
const showFormModal = ref(false)
const editingProvider = ref<ProviderResponse | null>(null)
const testingId = ref<number | null>(null)

const columns = [
  {
    title: t('name'),
    dataIndex: 'name',
    key: 'name',
    width: 160,
  },
  {
    title: t('settingCenter.aiProvider.type'),
    dataIndex: 'provider_type',
    key: 'provider_type',
    width: 140,
    customRender: ({ record }: { record: ProviderResponse }) => {
      const typeLabels: Record<string, string> = {
        deepseek: 'DeepSeek',
        openai_compatible: 'OpenAI Compatible',
        custom: t('settingCenter.aiProvider.customType'),
        maas: 'MaaS',
      }
      const typeColors: Record<string, string> = {
        deepseek: 'blue',
        openai_compatible: 'green',
        custom: 'orange',
        maas: 'purple',
      }
      return h(Tag, { color: typeColors[record.provider_type] || 'default' }, () =>
        typeLabels[record.provider_type] || record.provider_type,
      )
    },
  },
  {
    title: 'Base URL',
    dataIndex: 'base_url',
    key: 'base_url',
    ellipsis: true,
  },
  {
    title: 'API Key',
    dataIndex: 'api_key_display',
    key: 'api_key_display',
    width: 160,
  },
  {
    title: t('settingCenter.aiProvider.models'),
    dataIndex: 'models',
    key: 'models',
    width: 200,
    customRender: ({ record }: { record: ProviderResponse }) => {
      if (!record.models || record.models.length === 0) {
        return h('span', { class: 'text-gray-400' }, '—')
      }
      return h(Space, { wrap: true, size: [0, 4] }, () =>
        record.models!.slice(0, 3).map(m =>
          h(Tag, { color: 'default', size: 'small' }, () => m),
        ).concat(
          record.models!.length > 3
            ? [h(Tag, { size: 'small' }, () => `+${record.models!.length - 3}`)]
            : [],
        ),
      )
    },
  },
  {
    title: t('settingCenter.aiProvider.status'),
    dataIndex: 'is_default',
    key: 'status',
    width: 100,
    align: 'center',
    customRender: ({ record }: { record: ProviderResponse }) => {
      if (record.is_default) {
        return h(Tag, { color: 'success' }, () => t('settingCenter.aiProvider.default'))
      }
      if (!record.is_active) {
        return h(Tag, { color: 'default' }, () => t('settingCenter.aiProvider.inactive'))
      }
      return h('span', { class: 'text-gray-400' }, '—')
    },
  },
  {
    title: t('operate'),
    key: 'operate',
    width: 200,
    align: 'center',
    customRender: ({ record }: { record: ProviderResponse }) =>
      h(Space, [
        h(Tooltip, { title: t('settingCenter.aiProvider.testConnection') }, () =>
          h(
            Button,
            {
              type: 'link',
              size: 'small',
              loading: testingId.value === record.id,
              onClick: () => handleTest(record),
            },
            () => h(ApiOutlined),
          ),
        ),
        h(Tooltip, { title: t('edit') }, () =>
          h(
            Button,
            {
              type: 'link',
              size: 'small',
              onClick: () => handleEdit(record),
            },
            () => h(EditOutlined),
          ),
        ),
        h(Popconfirm, {
          title: t('settingCenter.aiProvider.deleteConfirm'),
          onConfirm: () => handleDelete(record),
        }, () =>
          h(
            Button,
            { type: 'link', size: 'small', danger: true },
            () => h(DeleteOutlined),
          ),
        ),
      ]),
  },
]

async function fetchProviders() {
  loading.value = true
  try {
    providers.value = await getProviders()
  }
  catch {
    message.error(t('settingCenter.aiProvider.fetchFailed'))
  }
  finally {
    loading.value = false
  }
}

function handleAdd() {
  editingProvider.value = null
  showFormModal.value = true
}

function handleEdit(record: ProviderResponse) {
  editingProvider.value = { ...record }
  showFormModal.value = true
}

function handleFormSuccess() {
  showFormModal.value = false
  editingProvider.value = null
  fetchProviders()
}

async function handleDelete(record: ProviderResponse) {
  try {
    await deleteProvider(record.id)
    message.success(t('deleteSuccess'))
    fetchProviders()
  }
  catch {
    message.error(t('settingCenter.aiProvider.deleteFailed'))
  }
}

async function handleTest(record: ProviderResponse) {
  testingId.value = record.id
  try {
    const result = await testProvider(record.id)
    if (result.success) {
      message.success(`${t('settingCenter.aiProvider.testSuccess')} (${result.models.length} models)`)
    }
    else {
      message.error(`${t('settingCenter.aiProvider.testFailed')}: ${result.message}`)
    }
  }
  catch {
    message.error(t('settingCenter.aiProvider.testFailed'))
  }
  finally {
    testingId.value = null
  }
}

onMounted(() => {
  fetchProviders()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="flex items-center justify-between mb-4">
      <span class="text-sm text-gray-500">
        {{ t('settingCenter.aiProvider.description') }}
      </span>
      <Button type="primary" size="small" @click="handleAdd">
        <PlusOutlined />
        {{ t('settingCenter.aiProvider.addProvider') }}
      </Button>
    </div>
    <div class="flex-1 overflow-auto">
      <Table
        :columns="columns"
        :data-source="providers"
        :loading="loading"
        :pagination="false"
        row-key="id"
        size="small"
        bordered
      >
        <template #empty>
          <Empty :description="t('settingCenter.aiProvider.noProvider')" />
        </template>
      </Table>
    </div>
    <ProviderFormModal
      v-model:open="showFormModal"
      :provider="editingProvider"
      @success="handleFormSuccess"
    />
  </div>
</template>
