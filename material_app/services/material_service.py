from material_app.models import MaterialOverview

class MaterialService:

    @staticmethod
    def get_items_by_box(box_id):
        """取得指定容器內的所有物品"""
        from material_app.repositories.material_repository import MaterialRepository
        return MaterialRepository.get_items_by_box(box_id)

    @staticmethod
    def get_box_by_id(box_id):
        """根據 BoxID 取得單一容器資訊"""
        from material_app.repositories.material_repository import MaterialRepository
        boxes = MaterialRepository.get_all_boxes()
        return boxes.get(box_id)



    @staticmethod
    def get_all_boxes():
        return MaterialOverview.objects.all().order_by("-CreateDate")

    @staticmethod
    def add_box(data):
        return MaterialOverview.objects.create(**data)

    @staticmethod
    def update_box(box_id, data):
        return MaterialOverview.objects.filter(BoxID=box_id).update(**data)

    @staticmethod
    def delete_box(box_id):
        return MaterialOverview.objects.filter(BoxID=box_id).delete()
