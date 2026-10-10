<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { fetchCategories, createCategory, updateCategory, deleteCategory, type Category } from '@/api'

const list = ref<Category[]>([])
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '', sortOrder: 0 })

const rules: FormRules = {
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

async function load() {
  loading.value = true
  try {
    list.value = await fetchCategories()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', description: '', sortOrder: 0 })
  dialog.value = true
}

function openEdit(row: Category) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, description: row.description, sortOrder: row.sortOrder })
  dialog.value = true
}

async function save() {
  await formRef.value?.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    if (editingId.value == null) {
      await createCategory({ ...form })
      ElMessage.success('新增成功')
    } else {
      await updateCategory(editingId.value, { ...form })
      ElMessage.success('保存成功')
    }
    dialog.value = false
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}

async function onDelete(row: Category) {
  await ElMessageBox.confirm(
    row.productCount > 0
      ? `分类「${row.name}」下还有 ${row.productCount} 个菜品，删除可能失败，确定继续吗？`
      : `确认删除分类「${row.name}」吗？`,
    '删除确认',
    { type: 'warning' },
  )
  try {
    await deleteCategory(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">分类列表</span>
        <el-button type="primary" @click="openCreate">新增分类</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="description" label="描述" min-width="160">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column prop="sortOrder" label="排序" width="90" />
        <el-table-column prop="productCount" label="菜品数" width="90" />
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="editingId == null ? '新增分类' : '编辑分类'" width="420px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="70px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="20" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="100" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" :precision="0" style="width: 140px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.toolbar-title { font-size: 15px; font-weight: 600; }
</style>
