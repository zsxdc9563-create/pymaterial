from ..models import BOMReleaseLog

# 查這個 box 底下所有已完成出庫的 item id
done_item_ids = set(
    BOMReleaseLog.objects.filter(
        release__status='DONE',
        is_shortage=False,
        item__box_id=box_id,
    ).values_list('item_id', flat=True)
)

# 序列化時帶入 context
serializer = MaterialSerializer(
    items,
    many=True,
    context={'done_item_ids': done_item_ids}
)