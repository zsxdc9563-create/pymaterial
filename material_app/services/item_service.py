from material_app.models import MaterialItems

class ItemService:
    @staticmethod
    def add_item(data):
        return MaterialItems.objects.create(**data)

    @staticmethod
    def get_items_by_box(box_id):
        return MaterialItems.objects.filter(BoxID=box_id)

    @staticmethod
    def update_item(sn, data):
        return MaterialItems.objects.filter(SN=sn).update(**data)

    @staticmethod
    def delete_item(sn):
        return MaterialItems.objects.filter(SN=sn).delete()

