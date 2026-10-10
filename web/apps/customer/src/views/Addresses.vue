<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showToast } from 'vant'
import { addressApi } from '@/api'
import type { Address } from '@/api'

const router = useRouter()

const list = ref<Address[]>([])
const loading = ref(true)
const showForm = ref(false)
const editing = ref<Address>()
const saving = ref(false)

const form = ref({ name: '', phone: '', detail: '', province: '', city: '', district: '', isDefault: false })

async function load() {
  loading.value = true
  try {
    list.value = await addressApi.list()
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editing.value = undefined
  form.value = { name: '', phone: '', detail: '', province: '', city: '', district: '', isDefault: false }
  showForm.value = true
}

function openEdit(a: Address) {
  editing.value = a
  form.value = {
    name: a.name,
    phone: a.phone,
    detail: a.detail,
    province: a.province || '',
    city: a.city || '',
    district: a.district || '',
    isDefault: a.isDefault,
  }
  showForm.value = true
}

async function save() {
  if (!form.value.name.trim()) return showToast('请填写联系人')
  if (!/^1\d{10}$/.test(form.value.phone)) return showToast('请填写正确手机号')
  if (!form.value.detail.trim()) return showToast('请填写详细地址')
  saving.value = true
  try {
    if (editing.value) await addressApi.update(editing.value.id, form.value)
    else await addressApi.create(form.value)
    showToast('保存成功')
    showForm.value = false
    load()
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function remove(a: Address) {
  await showConfirmDialog({ title: '提示', message: `删除「${a.name}」的地址？` })
  try {
    await addressApi.remove(a.id)
    showToast('已删除')
    load()
  } catch (e) {
    showToast((e as Error).message)
  }
}

onMounted(load)
</script>

<template>
  <div class="addr-page">
    <van-nav-bar title="地址管理" left-arrow @click-left="router.back()" />

    <div class="list">
      <van-swipe-cell v-for="a in list" :key="a.id">
        <div class="addr-card" @click="openEdit(a)">
          <div class="a-left">
            <div class="a-line1">
              {{ a.name }} <span class="a-phone">{{ a.phone }}</span>
              <van-tag v-if="a.isDefault" type="warning" class="a-tag">默认</van-tag>
            </div>
            <div class="a-line2">{{ a.province }}{{ a.city }}{{ a.district }}{{ a.detail }}</div>
          </div>
          <van-icon name="edit" @click.stop="openEdit(a)" />
        </div>
        <template #right>
          <van-button square type="danger" text="删除" class="del-btn" @click="remove(a)" />
        </template>
      </van-swipe-cell>
      <van-empty v-if="!loading && !list.length" description="还没有收货地址" />
    </div>

    <div class="footer">
      <van-button type="primary" block round icon="plus" @click="openAdd">新增地址</van-button>
    </div>

    <van-popup v-model:show="showForm" position="bottom" round :style="{ minHeight: '50vh' }">
      <div class="form-panel">
        <div class="f-title">{{ editing ? '编辑地址' : '新增地址' }}</div>
        <van-field v-model="form.name" label="联系人" placeholder="收货人姓名" />
        <van-field v-model="form.phone" label="手机号" type="tel" maxlength="11" placeholder="收货人手机号" />
        <van-field v-model="form.detail" label="详细地址" placeholder="街道、门牌号" />
        <van-field v-model="form.province" label="省份" placeholder="选填" />
        <van-field v-model="form.city" label="城市" placeholder="选填" />
        <van-field v-model="form.district" label="区县" placeholder="选填" />
        <van-cell title="设为默认地址">
          <template #right-icon>
            <van-switch v-model="form.isDefault" size="22" />
          </template>
        </van-cell>
        <van-button type="primary" block round class="f-save" :loading="saving" @click="save">保存</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.addr-page {
  min-height: 100vh;
  padding-bottom: 90px;
}
.list {
  padding: 12px;
}
.addr-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  border-radius: 10px;
  padding: 14px 12px;
  margin-bottom: 10px;
}
.a-left {
  flex: 1;
  min-width: 0;
}
.a-line1 {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.a-phone {
  font-size: 13px;
  font-weight: 400;
  color: #969799;
}
.a-tag {
  flex-shrink: 0;
}
.a-line2 {
  font-size: 13px;
  color: #969799;
  margin-top: 4px;
}
.del-btn {
  height: 100%;
}
.footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  max-width: 750px;
  margin: 0 auto;
  padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
  background: #fff;
}
.form-panel {
  padding: 20px 0 28px;
}
.f-title {
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 10px;
}
.f-save {
  margin: 20px 16px 0;
  width: calc(100% - 32px);
}
</style>
