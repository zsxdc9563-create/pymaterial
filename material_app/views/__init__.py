# views/__init__.py

from .box_views import (
    index,
    box_list,
    box_add,
    box_edit,
    box_delete,
    box_toggle_lock,
    box_checkin,
    box_bom,
    box_export_excel,
    box_import_excel,
    box_download_template,
)

from .material_views import (
    material_list,
    material_add,
    material_edit,
    material_delete,
)

from .transaction_views import (
    transaction_transfer,
    transaction_history,
)

from . import borrow_views