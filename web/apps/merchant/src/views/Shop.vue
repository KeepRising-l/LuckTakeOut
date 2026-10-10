<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { fetchCurrent, updateMerchantInfo, updateMerchantStatus, uploadAvatar } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const saving = ref(false)
const open = ref(true)
const logo = ref('')
const form = reactive({
  name: '',
  phone: '',
  address: '',
  description: '',
  openTime: '',
  closeTime: '',
})

async function load() {
  try {
    const data = await fetchCurrent()
    Object.assign(form, {
      name: data.name,
      phone: data.phone,
      address: data.address,
      description: data.description,
      openTime: data.openTime || '',
      closeTime: data.closeTime || '',
    })
    logo.value = data.logo || data.avatar || ''
    open.value = data.open !== false
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('店铺名称不能为空')
    return
  }
  saving.value = true
  try {
    await updateMerchantInfo({
      name: form.name,
      phone: form.phone,
      address: form.address,
      description: form.description,
    })
    auth.setAvatar(logo.value)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function onUpload(opt: UploadRequestOptions) {
  try {
    const data = await uploadAvatar(opt.file as File)
    logo.value = data.logo
    auth.setAvatar(data.logo)
    ElMessage.success('头像已更新')
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onOpenChange(val: boolean) {
  try {
    await updateMerchantStatus(val)
    ElMessage.success(val ? '店铺已开启营业' : '店铺已暂停营业')
  } catch (e) {
    open.value = !val
    ElMessage.error((e as Error).message)
  }
}

onMounted(load)
</script>

<template>
  <div class="shop">
    <el-card shadow="never" style="max-width: 640px">
      <template #header>店铺信息</template>

      <div class="logo-row">
        <el-upload
          :show-file-list="false"
          accept=".jpg,.jpeg,.png,.webp,.gif"
          :http-request="onUpload"
        >
          <el-avatar :size="72" :src="logo || undefined" shape="square">
            {{ (form.name || '店').slice(0, 1) }}
          </el-avatar>
        </el-upload>
        <div class="logo-tip">
          <div class="logo-title">店铺头像</div>
          <div class="logo-sub">点击头像更换，支持 jpg/png/webp/gif，不超过 5MB</div>
        </div>
      </div>

      <el-form label-width="90px" style="margin-top: 18px">
        <el-form-item label="店铺名称" required>
          <el-input v-model="form.name" maxlength="30" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.phone" maxlength="20" />
        </el-form-item>
        <el-form-item label="店铺地址">
          <el-input v-model="form.address" maxlength="100" />
        </el-form-item>
        <el-form-item label="店铺公告">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
        <el-form-item label="营业时间">
          <span class="time-text">{{ form.openTime || '--:--' }} ~ {{ form.closeTime || '--:--' }}</span>
        </el-form-item>
        <el-form-item label="营业状态">
          <el-switch v-model="open" active-text="营业中" inactive-text="已打烊" @change="onOpenChange" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.logo-row { display: flex; align-items: center; gap: 16px; }
.logo-title { font-size: 15px; font-weight: 600; }
.logo-sub { font-size: 12px; color: #909399; margin-top: 4px; }
.time-text { color: #606266; }
</style>
