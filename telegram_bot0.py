@@
 from telegram.ext import (
@@
 )
+from google_maps_route import get_routes   # <-- импорт новой функции
 
@@  async def receive_end_pc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
     dest_pc = (update.message.text or "").strip().upper()
     context.user_data["dest_pc"] = dest_pc
-    await update.message.reply_text(
-        f"✅ Saved!\n🗺️ Route: {context.user_data['start_pc']} → {dest_pc}"
-    )
+    await update.message.reply_text("⏳ Calculating routes, please wait…")
+
+    try:
+        routes = await get_routes(context.user_data["start_pc"], dest_pc)
+    except Exception as e:
+        await update.message.reply_text(f"❌ Google Maps error: {e}")
+        return ConversationHandler.END
+
+    # Формируем читаемый ответ
+    lines = []
+    for idx, r in enumerate(routes, start=1):
+        lines.append(f"Route {idx}: {r['distance_km']} km, {r['duration_text']}")
+
+    # Если ни одного варианта не пришло
+    if not lines:
+        lines = ["❗ No route found"]
+
+    await update.message.reply_text("\n".join(lines))
 
     return ConversationHandler.END  # диалог завершён
