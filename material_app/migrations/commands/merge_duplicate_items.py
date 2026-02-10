# material_app/management/commands/merge_duplicate_items.py
#合併重複記錄
from django.core.management.base import BaseCommand
from material_app.models import MaterialItems
from django.db import connection, transaction


class Command(BaseCommand):
    help = '合併重複的物品記錄（更新外鍵引用後刪除重複項）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示會執行的操作，不實際執行',
        )
        parser.add_argument(
            '--sn',
            type=str,
            help='只處理特定的 SN',
        )

    def handle(self, *args, **options):
        # 找出所有重複的 (SN, BoxID) 組合
        with connection.cursor() as cursor:
            if options['sn']:
                cursor.execute("""
                    SELECT SN, BoxID_id, COUNT(*) as count
                    FROM material_app_itemlist
                    WHERE SN = %s
                    GROUP BY SN, BoxID_id
                    HAVING count > 1
                    ORDER BY count DESC
                """, [options['sn']])
            else:
                cursor.execute("""
                    SELECT SN, BoxID_id, COUNT(*) as count
                    FROM material_app_itemlist
                    GROUP BY SN, BoxID_id
                    HAVING count > 1
                    ORDER BY count DESC
                """)

            duplicates = cursor.fetchall()

        if not duplicates:
            self.stdout.write(self.style.SUCCESS('✅ 沒有發現重複的記錄'))
            return

        self.stdout.write(self.style.WARNING(f'⚠️ 發現 {len(duplicates)} 組重複記錄\n'))

        total_merged = 0

        for sn, box_id, count in duplicates:
            self.stdout.write(f'\n📦 處理: SN={sn}, BoxID={box_id} (共 {count} 筆)')

            # 取得該組合的所有記錄（按更新時間排序，保留最新的）
            items = MaterialItems.objects.filter(
                SN=sn,
                BoxID_id=box_id
            ).order_by('-UpdateTime', '-id')

            kept_item = items.first()
            duplicates_to_merge = items.exclude(id=kept_item.id)

            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ 保留: ID={kept_item.id}, ItemName={kept_item.ItemName}, '
                    f'Quantity={kept_item.Quantity}, UpdateTime={kept_item.UpdateTime}'
                )
            )

            # 處理每一筆重複記錄
            for dup_item in duplicates_to_merge:
                self.stdout.write(
                    self.style.WARNING(
                        f'  ✗ 合併: ID={dup_item.id}, ItemName={dup_item.ItemName}, '
                        f'Quantity={dup_item.Quantity}, UpdateTime={dup_item.UpdateTime}'
                    )
                )

                # 檢查是否有交易記錄引用
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM material_app_transactionlog
                        WHERE SN_id = %s
                    """, [dup_item.id])
                    transaction_count = cursor.fetchone()[0]

                if transaction_count > 0:
                    self.stdout.write(f'    → 發現 {transaction_count} 筆交易記錄引用此項目')

                if not options['dry_run']:
                    try:
                        with transaction.atomic():
                            # 步驟 1: 更新所有引用此重複記錄的交易記錄
                            if transaction_count > 0:
                                with connection.cursor() as cursor:
                                    cursor.execute("""
                                        UPDATE material_app_transactionlog
                                        SET SN_id = %s
                                        WHERE SN_id = %s
                                    """, [kept_item.id, dup_item.id])
                                    updated = cursor.rowcount
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'    → 已更新 {updated} 筆交易記錄'
                                        )
                                    )

                            # 步驟 2: 刪除重複記錄
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    DELETE FROM material_app_itemlist
                                    WHERE id = %s
                                """, [dup_item.id])
                                self.stdout.write(
                                    self.style.SUCCESS(f'    → 已刪除重複記錄 ID={dup_item.id}')
                                )

                            total_merged += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ 合併失敗: {e}')
                        )

        self.stdout.write(f'\n總計: {total_merged} 筆記錄已合併')

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    '\n💡 這是模擬執行，沒有實際修改資料。'
                    '\n   移除 --dry-run 參數來實際執行合併。'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ 重複記錄合併完成'))