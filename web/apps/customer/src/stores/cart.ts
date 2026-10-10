import { defineStore } from 'pinia'
import { storage } from '@takeout/shared'
import type { Merchant, Product } from '@/api'

export interface CartItem {
  productId: number
  name: string
  price: number
  image: string
  quantity: number
  checked: boolean
}

export interface MerchantCart {
  merchantId: number
  merchantName: string
  deliveryFee: number
  items: CartItem[]
}

const KEY = 'customerCart'

function load(): MerchantCart[] {
  return storage.getJSON<MerchantCart[]>(KEY) || []
}

function save(carts: MerchantCart[]) {
  storage.setJSON(KEY, carts)
}

export const useCartStore = defineStore('cart', {
  state: () => ({
    carts: load() as MerchantCart[],
  }),
  getters: {
    /** 全部商品总件数 */
    totalCount: (s): number =>
      s.carts.reduce((n, m) => n + m.items.reduce((k, i) => k + i.quantity, 0), 0),
  },
  actions: {
    merchantCart(merchantId: number): MerchantCart | undefined {
      return this.carts.find((m) => m.merchantId === merchantId)
    },
    /** 加入购物车（同商家数量 +1，跨商家新开一组） */
    add(merchant: Pick<Merchant, 'id' | 'name' | 'deliveryFee'>, product: Product) {
      let mc = this.merchantCart(merchant.id)
      if (!mc) {
        mc = { merchantId: merchant.id, merchantName: merchant.name, deliveryFee: merchant.deliveryFee, items: [] }
        this.carts.push(mc)
      }
      const item = mc.items.find((i) => i.productId === product.id)
      if (item) item.quantity += 1
      else
        mc.items.push({
          productId: product.id,
          name: product.name,
          price: product.price,
          image: product.image || product.mainImage || product.productImage || '',
          quantity: 1,
          checked: true,
        })
      save(this.carts)
    },
    /** 设置数量，减到 0 移除商品 */
    setCount(merchantId: number, productId: number, count: number) {
      const mc = this.merchantCart(merchantId)
      if (!mc) return
      const idx = mc.items.findIndex((i) => i.productId === productId)
      if (idx < 0) return
      if (count <= 0) mc.items.splice(idx, 1)
      else mc.items[idx].quantity = count
      if (!mc.items.length) this.carts = this.carts.filter((m) => m.merchantId !== merchantId)
      save(this.carts)
    },
    removeItems(merchantId: number, productIds: number[]) {
      const mc = this.merchantCart(merchantId)
      if (!mc) return
      mc.items = mc.items.filter((i) => !productIds.includes(i.productId))
      if (!mc.items.length) this.carts = this.carts.filter((m) => m.merchantId !== merchantId)
      save(this.carts)
    },
    toggleItem(merchantId: number, productId: number) {
      const item = this.merchantCart(merchantId)?.items.find((i) => i.productId === productId)
      if (item) {
        item.checked = !item.checked
        save(this.carts)
      }
    },
    toggleAll(merchantId: number, checked: boolean) {
      const mc = this.merchantCart(merchantId)
      if (!mc) return
      mc.items.forEach((i) => (i.checked = checked))
      save(this.carts)
    },
    clearMerchant(merchantId: number) {
      this.carts = this.carts.filter((m) => m.merchantId !== merchantId)
      save(this.carts)
    },
    quantityOf(merchantId: number, productId: number): number {
      return this.merchantCart(merchantId)?.items.find((i) => i.productId === productId)?.quantity || 0
    },
  },
})
