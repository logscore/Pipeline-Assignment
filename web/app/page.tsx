import Link from "next/link";
import { ArrowRight, ShoppingCart, ListChecks, Factory } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center -mt-8 sm:-mt-16 w-full">
      {/* Background decoration */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[40%] text-transparent -left-[10%] w-[70%] h-[70%] rounded-full bg-gradient-to-br from-indigo-100/40 to-purple-100/40 blur-3xl opacity-50 dark:from-indigo-900/40 dark:to-purple-900/40" />
        <div className="absolute top-[20%] text-transparent -right-[10%] w-[60%] h-[60%] rounded-full bg-gradient-to-tl from-emerald-100/40 to-teal-100/40 blur-3xl opacity-50 dark:from-emerald-900/40 dark:to-teal-900/40" />
      </div>

      <main className="relative z-10 flex flex-col items-center w-full max-w-5xl px-6 py-12 xs:py-24 space-y-16">
        
        {/* Hero Section */}
        <div className="flex flex-col items-center text-center space-y-6">
          <div className="inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50/50 px-3 py-1 text-sm font-medium text-indigo-800 backdrop-blur-sm">
            <span className="flex h-2 w-2 rounded-full bg-indigo-600 mr-2 animate-pulse"></span>
            System Online
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-slate-800">
            Intelligent{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
              Order Pipeline
            </span>
          </h1>
          
          <p className="max-w-2xl text-lg md:text-xl text-slate-600 leading-relaxed">
            Manage customer orders and leverage machine learning to optimize warehouse fulfillment priorities in real-time.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Link 
              href="/place-order" 
              className="group relative inline-flex items-center justify-center gap-2 rounded-full bg-slate-900 px-8 py-3.5 text-sm font-medium text-white shadow-lg shadow-slate-900/20 transition-all hover:bg-slate-800 hover:-translate-y-0.5"
            >
              Start New Order
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid w-full gap-6 sm:grid-cols-2 lg:grid-cols-3 pt-8">
          
          {/* Feature 1 */}
          <Link href="/place-order" className="group flex flex-col justify-between rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200/50 transition-all hover:shadow-xl hover:shadow-indigo-100 hover:ring-indigo-200">
            <div>
              <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300">
                <ShoppingCart className="h-6 w-6" />
              </div>
              <h3 className="mb-3 text-xl font-semibold text-slate-800">Place Order</h3>
              <p className="text-slate-600 leading-relaxed">
                Create new orders for customers and simulate automated entry into the fulfillment pipeline.
              </p>
            </div>
          </Link>

          {/* Feature 2 */}
          <Link href="/orders" className="group flex flex-col justify-between rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200/50 transition-all hover:shadow-xl hover:shadow-purple-100 hover:ring-purple-200">
            <div>
              <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-purple-50 text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors duration-300">
                <ListChecks className="h-6 w-6" />
              </div>
              <h3 className="mb-3 text-xl font-semibold text-slate-800">Order History</h3>
              <p className="text-slate-600 leading-relaxed">
                View previously placed orders, check their statuses, and inspect individual order details.
              </p>
            </div>
          </Link>

          {/* Feature 3 */}
          <Link href="/warehouse/priority" className="group flex flex-col justify-between rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200/50 transition-all hover:shadow-xl hover:shadow-emerald-100 hover:ring-emerald-200 sm:col-span-2 lg:col-span-1">
            <div>
              <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors duration-300">
                <Factory className="h-6 w-6" />
              </div>
              <h3 className="mb-3 text-xl font-semibold text-slate-800">Warehouse Priority</h3>
              <p className="text-slate-600 leading-relaxed">
                Review the priority queue generated by the ML model to optimize order pick-up and processing.
              </p>
            </div>
          </Link>

        </div>
      </main>
    </div>
  );
}
