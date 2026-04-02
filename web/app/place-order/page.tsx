import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { db } from "@/db";
import { products } from "@/db/schema";
import OrderClient from "./OrderClient";

type Product = typeof products.$inferSelect;

export default async function PlaceOrderPage() {
  const cookieStore = await cookies();
  const customerIdStr = cookieStore.get("selected_customer_id")?.value;

  if (!customerIdStr) {
    redirect("/select-customer");
  }

  let allProducts: Product[] = [];
  try {
    allProducts = await db.select().from(products);
  } catch (err) {
    console.error("DB Error getting products:", err);
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-gray-900">
        Place a New Order
      </h1>
      <OrderClient availableProducts={allProducts} />
    </div>
  );
}
