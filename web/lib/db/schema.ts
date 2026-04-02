import { relations } from "drizzle-orm";
import {
  boolean,
  index,
  integer,
  pgTable,
  real,
  serial,
  text,
  timestamp,
} from "drizzle-orm/pg-core";

export const user = pgTable("user", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  emailVerified: boolean("email_verified").default(false).notNull(),
  image: text("image"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at")
    .defaultNow()
    .$onUpdate(() => /* @__PURE__ */ new Date())
    .notNull(),
});

export const session = pgTable(
  "session",
  {
    id: text("id").primaryKey(),
    expiresAt: timestamp("expires_at").notNull(),
    token: text("token").notNull().unique(),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .$onUpdate(() => /* @__PURE__ */ new Date())
      .notNull(),
    ipAddress: text("ip_address"),
    userAgent: text("user_agent"),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
  },
  (table) => [index("session_userId_idx").on(table.userId)],
);

export const account = pgTable(
  "account",
  {
    id: text("id").primaryKey(),
    accountId: text("account_id").notNull(),
    providerId: text("provider_id").notNull(),
    userId: text("user_id")
      .notNull()
      .references(() => user.id, { onDelete: "cascade" }),
    accessToken: text("access_token"),
    refreshToken: text("refresh_token"),
    idToken: text("id_token"),
    accessTokenExpiresAt: timestamp("access_token_expires_at"),
    refreshTokenExpiresAt: timestamp("refresh_token_expires_at"),
    scope: text("scope"),
    password: text("password"),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .$onUpdate(() => /* @__PURE__ */ new Date())
      .notNull(),
  },
  (table) => [index("account_userId_idx").on(table.userId)],
);

export const verification = pgTable(
  "verification",
  {
    id: text("id").primaryKey(),
    identifier: text("identifier").notNull(),
    value: text("value").notNull(),
    expiresAt: timestamp("expires_at").notNull(),
    createdAt: timestamp("created_at").defaultNow().notNull(),
    updatedAt: timestamp("updated_at")
      .defaultNow()
      .$onUpdate(() => /* @__PURE__ */ new Date())
      .notNull(),
  },
  (table) => [index("verification_identifier_idx").on(table.identifier)],
);

export const userRelations = relations(user, ({ many }) => ({
  sessions: many(session),
  accounts: many(account),
}));

export const sessionRelations = relations(session, ({ one }) => ({
  user: one(user, {
    fields: [session.userId],
    references: [user.id],
  }),
}));

export const accountRelations = relations(account, ({ one }) => ({
  user: one(user, {
    fields: [account.userId],
    references: [user.id],
  }),
}));

export const customers = pgTable("customers", {
  customer_id: serial("customer_id").primaryKey(),
  first_name: text("first_name").notNull(),
  last_name: text("last_name").notNull(),
  email: text("email").notNull().unique(),
  birthdate: timestamp("birthdate", { mode: "string" }), // or date
  gender: text("gender"),
});

export const products = pgTable("products", {
  product_id: serial("product_id").primaryKey(),
  product_name: text("product_name").notNull(),
  price: real("price").notNull(),
  weight: real("weight"),
});

export const orders = pgTable("orders", {
  order_id: serial("order_id").primaryKey(),
  customer_id: integer("customer_id")
    .references(() => customers.customer_id)
    .notNull(),
  order_timestamp: timestamp("order_timestamp", { mode: "string" })
    .defaultNow()
    .notNull(),
  fulfilled: integer("fulfilled").default(0).notNull(),
  num_items: integer("num_items"),
  total_value: real("total_value"),
  avg_weight: real("avg_weight"),
  late_delivery: integer("late_delivery"), // 0 or 1
  is_fraud: integer("is_fraud").default(0), // based on practice chapter
});

export const order_items = pgTable("order_items", {
  id: serial("id").primaryKey(),
  order_id: integer("order_id")
    .references(() => orders.order_id)
    .notNull(),
  product_id: integer("product_id")
    .references(() => products.product_id)
    .notNull(),
  quantity: integer("quantity").notNull(),
  unit_price: real("unit_price").notNull(),
  line_total: real("line_total").notNull(),
});

export const order_predictions = pgTable("order_predictions", {
  order_id: integer("order_id")
    .primaryKey()
    .references(() => orders.order_id),
  late_delivery_probability: real("late_delivery_probability"),
  predicted_late_delivery: integer("predicted_late_delivery"),
  prediction_timestamp: timestamp("prediction_timestamp", { mode: "string" }),
});

export const shipments = pgTable("shipments", {
  shipment_id: serial("shipment_id").primaryKey(),
  order_id: integer("order_id")
    .references(() => orders.order_id)
    .notNull(),
  carrier: text("carrier"),
  shipping_method: text("shipping_method"),
  distance_band: text("distance_band"),
  promised_days: real("promised_days"),
  actual_days: real("actual_days"),
  late_delivery: integer("late_delivery"),
});
