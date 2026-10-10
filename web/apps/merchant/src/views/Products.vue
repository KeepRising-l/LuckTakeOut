<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  fetchProducts, createProduct, updateProduct, deleteProduct,
  updateProductStatus, updateProductStock, fetchCategories,
  type Product, type Category,
} from '@/api'
import { money } from '@takeout/shared'

const list = ref<Product[]>([])
const categories = ref<Category[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)

const dialog = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '', price: 1, stock: 0, categoryId: null as number | null })

const rules: FormRules = {
  name: [{ required: true, message: '请输入菜品名称', trigger: 'blur' }],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    { type: 'number', validator: (_r, v: number, cb) => (v > 0 ? cb() : cb(new Error('价格必须大于 0'))), trigger: 'blur' },
  ],
  stock: [
    { required: true, message: '请输入库存', trigger: 'blur' },
    { type: 'number', validator: (_r, v: number, cb) => (Number.isInteger(v) && v >= 0 ? cb() : cb(new Error('库存须为非负整数'))), trigger: 'blur' },
  ],
}

async function load() {
  loading.value = true
  try {
    const [data, cats] = await Promise.all([
      fetchProducts({ page: page.value, size: size.value }),
      fetchCategories(),
    ])
    list.value = data.items || []
    total.value = data.total || 0
    categories.value = cats
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  load()
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', description: '', price: 1, stock: 0, categoryId: categories.value[0]?.id ?? null })
  dialog.value = true
}

function openEdit(row: Product) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name,
    description: row.description,
    price: row.price,
    stock: row.stock,
    categoryId: row.categoryId,
  })
  dialog.value = true
}

async function save() {
  await formRef.value?.validate().catch(() => Promise.reject())
  saving.value = true
  try {
    if (editingId.value == null) {
      await createProduct({ ...form })
      ElMessage.success('新增成功')
    } else {
      await updateProduct(editingId.value, { ...form })
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

async function onDelete(row: Product) {
  await ElMessageBox.confirm(`确认删除菜品「${row.name}」吗？`, '删除确认', { type: 'warning' })
  try {
    await deleteProduct(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onStatusChange(row: Product) {
  try {
    await updateProductStatus(row.id, row.status)
    ElMessage.success(row.status === 'ACTIVE' ? '已上架' : '已下架')
  } catch (e) {
    row.status = row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
    ElMessage.error((e as Error).message)
  }
}

async function onStockChange(row: Product) {
  try {
    await updateProductStock(row.id, row.stock)
  } catch (e) {
    ElMessage.error((e as Error).message)
    load()
  }
}

const imgSrc = (p: Product) => (p.image && !p.image.startsWith('http') ? p.image : p.image)

onMounted(load)
</script>

<template>
  <div>
    <el-card shadow="never">
      <div class="toolbar">
        <span class="toolbar-title">菜品列表</span>
        <el-button type="primary" @click="openCreate">新增菜品</el-button>
      </div>

      <el-table :data="list" v-loading="loading" stripe>
        <el-table-column label="图片" width="80">
          <template #default="{ row }">
            <el-image
              :src="imgSrc(row)"
              fit="cover"
              style="width: 48px; height: 48px; border-radius: 6px"
              v-if="row.image"
            />
            <div v-else class="img-placeholder">无图</div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="categoryName" label="分类" width="100">
          <template #default="{ row }">{{ row.categoryName || '-' }}</template>
        </el-table-column>
        <el-table-column label="价格" width="100">
          <template #default="{ row }">¥{{ money(row.price) }}</template>
        </el-table-column>
        <el-table-column label="库存" width="130">
          <template #default="{ row }">
            <el-input-number
              v-model="row.stock"
              :min="0"
              :step="1"
              size="small"
              @change="onStockChange(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="上架状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.status"
              active-value="ACTIVE"
              inactive-value="INACTIVE"
              @change="onStatusChange(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="size"
        :current-page="page"
        @current-change="onPage"
      />
    </el-card>

    <el-dialog
      v-model="dialog"
      :title="editingId == null ? '新增菜品' : '编辑菜品'"
      width="480px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="分类" prop="categoryId">
          <el-select v-model="form.categoryId" placeholder="选择分类" clearable style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格(元)" prop="price">
          <el-input-number v-model="form.price" :min="0.01" :precision="2" :step="1" style="width: 160px" />
        </el-form-item>
        <el-form-item label="库存" prop="stock">
          <el-input-number v-model="form.stock" :min="0" :step="1" :precision="0" style="width: 160px" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="200" />
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
.pager { margin-top: 14px; justify-content: flex-end; }
.img-placeholder {
  width: 48px; height: 48px; border-radius: 6px;
  background: #f5f6f8; color: #c0c4cc;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
}
</style>
