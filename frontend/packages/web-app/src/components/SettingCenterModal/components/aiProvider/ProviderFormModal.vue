<script setup lang="ts">
import { ApiOutlined } from '@ant-design/icons-vue'
import { Form, Input, Modal, Select, Switch, Tag, message } from 'ant-design-vue'
import { useTranslation } from 'i18next-vue'
import { computed, ref, watch } from 'vue'

import { createProvider, testProvider, updateProvider } from '@/api/aiProvider'
import type { ProviderResponse } from '@/api/aiProvider'

const { t } = useTranslation()

const props = defineProps<{
  open: boolean
  provider: ProviderResponse | null
}>()

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'success'): void
}>()

const isEdit = computed(() => !!props.provider)
const title = computed(() =>
  isEdit.value
    ? `${t('edit')} - ${props.provider?.name}`
    : t('settingCenter.aiProvider.addProvider'),
)

const loading = ref(false)
const testing = ref(false)
const testResult = ref<string | null>(null)
const formRef = ref()

const PROVIDER_TYPES = [
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'OpenAI Compatible', value: 'openai_compatible' },
  { label: t('settingCenter.aiProvider.customType'), value: 'custom' },
]

const DEEPSEEK_DEFAULT_URL = 'https://api.deepseek.com/v1'
const DEEPSEEK_DEFAULT_MODELS = ['deepseek-chat', 'deepseek-reasoner']

const formState = ref({
  name: '',
  provider_type: 'deepseek' as string,
  base_url: DEEPSEEK_DEFAULT_URL,
  api_key: '',
  models: [] as string[],
  is_default: false,
  is_active: true,
})

const modelInput = ref('')

watch(
  () => props.open,
  (val) => {
    if (val) {
      if (props.provider) {
        formState.value = {
          name: props.provider.name,
          provider_type: props.provider.provider_type,
          base_url: props.provider.base_url,
          api_key: '',
          models: props.provider.models || [],
          is_default: props.provider.is_default,
          is_active: props.provider.is_active,
        }
      }
      else {
        formState.value = {
          name: '',
          provider_type: 'deepseek',
          base_url: DEEPSEEK_DEFAULT_URL,
          api_key: '',
          models: DEEPSEEK_DEFAULT_MODELS,
          is_default: false,
          is_active: true,
        }
      }
      modelInput.value = ''
      testResult.value = null
    }
  },
)

watch(
  () => formState.value.provider_type,
  (val) => {
    if (val === 'deepseek' && !isEdit.value) {
      formState.value.base_url = DEEPSEEK_DEFAULT_URL
      formState.value.models = [...DEEPSEEK_DEFAULT_MODELS]
    }
  },
)

function addModel() {
  const val = modelInput.value.trim()
  if (val && !formState.value.models.includes(val)) {
    formState.value.models.push(val)
  }
  modelInput.value = ''
}

function removeModel(model: string) {
  formState.value.models = formState.value.models.filter(m => m !== model)
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  try {
    if (props.provider?.id) {
      const result = await testProvider(props.provider.id)
      testResult.value = result.success
        ? `OK - ${result.models.length} models available`
        : `FAIL: ${result.message}`
    }
    else {
      testResult.value = t('settingCenter.aiProvider.testAfterSave')
    }
  }
  catch (e: any) {
    testResult.value = `FAIL: ${e?.message || 'Unknown error'}`
  }
  finally {
    testing.value = false
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  }
  catch {
    return
  }

  loading.value = true
  try {
    const data = {
      name: formState.value.name,
      provider_type: formState.value.provider_type as any,
      base_url: formState.value.base_url,
      api_key: formState.value.api_key,
      models: formState.value.models.length > 0 ? formState.value.models : undefined,
      is_default: formState.value.is_default,
      is_active: formState.value.is_active,
    }

    if (isEdit.value && props.provider) {
      await updateProvider(props.provider.id, data)
      message.success(t('updateSuccess'))
    }
    else {
      await createProvider(data)
      message.success(t('createSuccess'))
    }
    emit('success')
  }
  catch {
    message.error(t('operationFailed'))
  }
  finally {
    loading.value = false
  }
}

function handleCancel() {
  emit('update:open', false)
}
</script>

<template>
  <Modal
    :open="open"
    :title="title"
    :confirm-loading="loading"
    width="560px"
    destroy-on-close
    @ok="handleSubmit"
    @cancel="handleCancel"
  >
    <Form
      ref="formRef"
      :model="formState"
      :label-col="{ span: 5 }"
      :wrapper-col="{ span: 19 }"
    >
      <Form.Item
        :label="t('settingCenter.aiProvider.providerName')"
        name="name"
        :rules="[{ required: true, message: t('settingCenter.aiProvider.nameRequired') }]"
      >
        <Input v-model:value="formState.name" :placeholder="t('settingCenter.aiProvider.namePlaceholder')" />
      </Form.Item>

      <Form.Item :label="t('settingCenter.aiProvider.type')" name="provider_type">
        <Select v-model:value="formState.provider_type" :options="PROVIDER_TYPES" />
      </Form.Item>

      <Form.Item
        :label="'Base URL'"
        name="base_url"
        :rules="[{ required: true, message: t('settingCenter.aiProvider.urlRequired') }]"
      >
        <Input v-model:value="formState.base_url" placeholder="https://api.deepseek.com/v1" />
      </Form.Item>

      <Form.Item :label="'API Key'" name="api_key">
        <Input.Password
          v-model:value="formState.api_key"
          :placeholder="isEdit ? t('settingCenter.aiProvider.keyEditHint') : 'sk-...'"
          autocomplete="new-password"
        />
      </Form.Item>

      <Form.Item :label="t('settingCenter.aiProvider.models')">
        <div class="flex flex-col gap-2">
          <div class="flex gap-2">
            <Input
              v-model:value="modelInput"
              :placeholder="t('settingCenter.aiProvider.modelPlaceholder')"
              size="small"
              @press-enter="addModel"
            />
            <a-button size="small" type="dashed" @click="addModel">
              {{ t('settingCenter.aiProvider.addModel') }}
            </a-button>
          </div>
          <div v-if="formState.models.length > 0" class="flex flex-wrap gap-1">
            <Tag
              v-for="model in formState.models"
              :key="model"
              closable
              @close="removeModel(model)"
            >
              {{ model }}
            </Tag>
          </div>
          <span v-else class="text-xs text-gray-400">{{ t('settingCenter.aiProvider.noModelHint') }}</span>
        </div>
      </Form.Item>

      <Form.Item :label="t('settingCenter.aiProvider.setDefault')">
        <Switch v-model:checked="formState.is_default" />
        <span class="ml-2 text-xs text-gray-400">{{ t('settingCenter.aiProvider.defaultHint') }}</span>
      </Form.Item>

      <Form.Item v-if="isEdit" :label="t('settingCenter.aiProvider.status')">
        <Switch v-model:checked="formState.is_active" />
        <span class="ml-2 text-xs text-gray-400">
          {{ formState.is_active ? t('settingCenter.aiProvider.active') : t('settingCenter.aiProvider.inactive') }}
        </span>
      </Form.Item>

      <Form.Item v-if="isEdit" :label="t('settingCenter.aiProvider.testConnection')">
        <a-button size="small" :loading="testing" @click="handleTest">
          <ApiOutlined />
          {{ t('settingCenter.aiProvider.testBtn') }}
        </a-button>
        <span v-if="testResult" class="ml-2 text-xs" :class="testResult.startsWith('OK') ? 'text-green-500' : 'text-red-500'">
          {{ testResult }}
        </span>
      </Form.Item>
    </Form>
  </Modal>
</template>
