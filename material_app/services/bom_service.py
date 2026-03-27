# material_app/services/bom_service.py
import logging

from django.db import transaction

from ..models import BOMNode, BOMRelease, BOMReleaseLog, MaterialItems
from .material_service import stock_out

logger = logging.getLogger(__name__)


# ── 工具函式 ──────────────────────────────────────────

def _expand_bom_tree(node: BOMNode, multiplier: int = 1) -> list[dict]:
    """
    遞迴展開 BOM 樹，回傳所有葉節點的需求清單。

    Args:
        node:       目前節點
        multiplier: 累積乘數（每往下一層就乘上父節點的 qty_required）

    Returns:
        [
            {
                'item':         MaterialItems 物件,
                'required_qty': int（已乘上所有父層數量）,
            },
            ...
        ]

    範例：
        產品A（root, produce_qty=2）
        └── 子組件B（qty_required=3）
            └── 零件C（qty_required=4, item=零件C）

        零件C 實際需求 = 2 × 3 × 4 = 24
    """
    result = []

    if node.item:
        # 葉節點：有對應的實際物料
        result.append({
            'item': node.item,
            'required_qty': node.qty_required * multiplier,
        })
    else:
        # 中間節點：繼續往下展開
        for child in node.children.select_related('item').all():
            result.extend(
                _expand_bom_tree(child, multiplier * node.qty_required)
            )

    return result


def _merge_requirements(requirements: list[dict]) -> list[dict]:
    """
    合併相同 item 的需求量（同一物料可能出現在 BOM 樹多個節點）。

    Args:
        requirements: _expand_bom_tree 回傳的清單

    Returns:
        合併後的清單，每個 item 只出現一次
    """
    merged = {}
    for req in requirements:
        item_id = req['item'].pk
        if item_id in merged:
            merged[item_id]['required_qty'] += req['required_qty']
        else:
            merged[item_id] = {
                'item': req['item'],
                'required_qty': req['required_qty'],
            }
    return list(merged.values())


# ── 主要服務函式 ──────────────────────────────────────

def check_bom_shortage(bom_root_id: int, produce_qty: int) -> list[dict]:
    """
    缺料預檢（純查詢，不異動庫存）。

    在真正出庫前先跑這個，讓使用者知道哪些料不夠。

    Args:
        bom_root_id: BOMNode pk（根節點）
        produce_qty: 要生產幾組

    Returns:
        [
            {
                'item_id':      int,
                'sn':           str,
                'item_name':    str,
                'required_qty': int,
                'available':    int,
                'shortage':     int,   # 0 表示足夠
                'is_shortage':  bool,
            },
            ...
        ]
    """
    root = BOMNode.objects.prefetch_related('children__children').get(pk=bom_root_id)
    requirements = _expand_bom_tree(root, multiplier=produce_qty)
    requirements = _merge_requirements(requirements)

    result = []
    for req in requirements:
        item = req['item']
        required = req['required_qty']
        shortage = max(0, required - item.quantity)
        result.append({
            'item_id':      item.pk,
            'sn':           item.sn,
            'item_name':    item.item_name,
            'required_qty': required,
            'available':    item.quantity,
            'shortage':     shortage,
            'is_shortage':  shortage > 0,
        })

    return result


@transaction.atomic
def release_bom(bom_root_id: int, produce_qty: int, operator) -> BOMRelease:
    """
    BOM 批次出庫。

    流程：
      1. 建立 BOMRelease（狀態：CHECKING）
      2. 展開 BOM 樹，計算所有物料需求量
      3. 缺料檢查 → 有缺料則標記 FAILED，回傳缺料清單
      4. 全部足夠 → 逐一呼叫 stock_out 扣庫存
      5. 寫入 BOMReleaseLog 明細
      6. 更新狀態為 DONE

    Args:
        bom_root_id: BOMNode pk（根節點）
        produce_qty: 要生產幾組
        operator:    User 物件

    Returns:
        BOMRelease 物件（可從 .logs.all() 取得明細）

    Raises:
        ValueError: 缺料（會附上缺料清單）
    """
    root = BOMNode.objects.prefetch_related('children__children').get(pk=bom_root_id)

    # Step 1：建立出庫單
    release = BOMRelease.objects.create(
        bom_root=root,
        produce_qty=produce_qty,
        status='CHECKING',
        created_by=operator,
    )

    # Step 2：展開 BOM 樹
    requirements = _expand_bom_tree(root, multiplier=produce_qty)
    requirements = _merge_requirements(requirements)

    # Step 3：缺料檢查
    shortage_list = []
    for req in requirements:
        item = MaterialItems.objects.select_for_update().get(pk=req['item'].pk)
        shortage = max(0, req['required_qty'] - item.quantity)
        if shortage > 0:
            shortage_list.append({
                'sn':           item.sn,
                'item_name':    item.item_name,
                'required_qty': req['required_qty'],
                'available':    item.quantity,
                'shortage':     shortage,
            })

    if shortage_list:
        # 有缺料 → 標記失敗，拋出例外讓 view 回傳缺料清單給前端
        release.status = 'FAILED'
        release.remark = '缺料，出庫取消'
        release.save()
        raise ValueError({'message': '缺料，無法出庫', 'shortage_list': shortage_list})

    # Step 4 & 5：全部足夠 → 逐一出庫並寫明細
    for req in requirements:
        item = req['item']
        required_qty = req['required_qty']

        # 呼叫 material_service 的 stock_out，保持邏輯統一
        stock_out(
            item_id=item.pk,
            qty=required_qty,
            operator=operator,
            remark=f'BOM 批次出庫 #{release.pk}',
        )

        BOMReleaseLog.objects.create(
            release=release,
            item=item,
            required_qty=required_qty,
            actual_qty=required_qty,
            is_shortage=False,
        )

    # Step 6：完成
    release.status = 'DONE'
    release.save()

    logger.info(f'BOM 批次出庫完成：release_id={release.pk}, produce_qty={produce_qty}')
    return release


def get_bom_tree(bom_root_id: int) -> dict:
    """
    取得 BOM 樹狀結構（純查詢，供前端渲染用）。

    Returns:
        遞迴巢狀 dict，結構對應 BOMNodeTreeSerializer
    """
    def build_tree(node):
        return {
            'id':           node.pk,
            'name':         node.name,
            'qty_required': node.qty_required,
            'level':        node.level,
            'item_sn':      node.item.sn if node.item else None,
            'children':     [build_tree(child) for child in node.children.all()],
        }

    root = BOMNode.objects.prefetch_related('children__children').get(pk=bom_root_id)
    return build_tree(root)