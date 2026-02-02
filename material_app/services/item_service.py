from material_app.models import ItemList

class ItemService:
    @staticmethod
    def add_item(data):
        return ItemList.objects.create(**data)

    @staticmethod
    def get_items_by_box(box_id):
        return ItemList.objects.filter(BoxID=box_id)

    @staticmethod
    def update_item(sn, data):
        return ItemList.objects.filter(SN=sn).update(**data)

    @staticmethod
    def delete_item(sn):
        return ItemList.objects.filter(SN=sn).delete()
