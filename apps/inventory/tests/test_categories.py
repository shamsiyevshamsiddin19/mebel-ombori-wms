"""Admin picks "Boshqa" in the material form and types a new category."""

from django.test import TestCase
from django.urls import reverse

from apps.inventory.forms import OTHER_CATEGORY
from apps.inventory.models import BaseMaterial, Category, MaterialCategory, MeasurementUnit, clear_category_cache
from apps.inventory.tests.factories import make_admin, make_material, make_user
from apps.users.models import UserRole


class NewCategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin()

    def setUp(self):
        # Each test's rows are rolled back; drop the per-process category cache with them.
        clear_category_cache()
        self.addCleanup(clear_category_cache)
        self.client.force_login(self.admin)
        self.url = reverse("inventory:material_create")

    def post(self, **extra):
        data = {"name": "Oyna 4 mm", "category": OTHER_CATEGORY, "new_category": "Oyna va ko'zgu",
                "unit_of_measure": MeasurementUnit.PIECE, "minimum_threshold": "0",
                "allowed_roles": [UserRole.SBORKACHI]}
        data.update(extra)
        return self.client.post(self.url, data)

    def test_built_in_categories_are_seeded_and_boshqa_is_offered(self):
        self.assertEqual(
            list(Category.objects.filter(is_active=True).values_list("code", flat=True)),
            ["HARDWARE", "KRASKA", "GRUNTOFKA", "LMDF", "LDSP", "FANER", "PVC", "DSP", "UPAKOVKA"],
        )
        page = self.client.get(self.url)
        self.assertContains(page, f'value="{OTHER_CATEGORY}"')
        self.assertContains(page, ">Boshqa</option>")
        self.assertContains(page, "Yangi kategoriya nomi")
        self.assertNotContains(page, 'value="SHEET"')

    def test_boshqa_with_offcut_support_and_sm_dimensions(self):
        response = self.post(
            name="MDF 18 mm",
            new_category="MDF",
            new_category_supports_offcuts="on",
            dim_unit="sm",
            length_mm="275",
            width_mm="183",
            allowed_roles=[UserRole.ARRACHI],
        )
        category = Category.objects.get(name="MDF")
        material = BaseMaterial.objects.get(name="MDF 18 mm")
        self.assertRedirects(response, reverse("inventory:kirim") + f"?material={material.pk}", fetch_redirect_response=False)
        self.assertTrue(category.supports_offcuts)
        self.assertTrue(material.supports_offcuts)
        self.assertEqual((material.whole_stock.length_mm, material.whole_stock.width_mm), (2750, 1830))

    def test_boshqa_creates_the_category_and_the_material(self):
        response = self.post()

        category = Category.objects.get(name="Oyna va ko'zgu")
        material = BaseMaterial.objects.get(name="Oyna 4 mm")
        self.assertRedirects(response, reverse("inventory:kirim") + f"?material={material.pk}", fetch_redirect_response=False)
        self.assertEqual(category.code, "OYNA_VA_KO_ZGU")
        self.assertEqual(material.category, category.code)
        self.assertEqual(material.allowed_roles, [UserRole.SBORKACHI])

        # It is now a normal choice: in the dropdown, the list filter, and the worker's chips.
        self.assertContains(self.client.get(self.url), f'<option value="{category.code}" >Oyna va ko&#x27;zgu</option>')
        self.assertContains(self.client.get(reverse("inventory:material_list")), "Oyna va ko&#x27;zgu")
        self.client.force_login(make_user("sbork", [UserRole.SBORKACHI]))
        self.assertContains(self.client.get(reverse("inventory:home")), "Oyna va ko&#x27;zgu")

    def test_name_is_required(self):
        response = self.post(new_category="   ")
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_category", response.context["form"].errors)
        self.assertFalse(Category.objects.filter(code__startswith="KATEGORIYA").exists())

    def test_existing_name_is_reused_not_duplicated(self):
        self.post(new_category="  furnitura ")
        self.assertEqual(Category.objects.filter(name__iexact="furnitura").count(), 1)
        self.assertEqual(BaseMaterial.objects.get(name="Oyna 4 mm").category, MaterialCategory.HARDWARE)

    def test_new_category_needs_a_trade(self):
        response = self.post(allowed_roles=[])
        self.assertEqual(response.status_code, 200)
        self.assertIn("allowed_roles", response.context["form"].errors)
        self.assertFalse(Category.objects.filter(name="Oyna va ko'zgu").exists())

    def test_an_invalid_form_does_not_leave_a_category_behind(self):
        response = self.post(name="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Category.objects.filter(name="Oyna va ko'zgu").exists())

    def test_existing_material_can_move_to_a_new_category(self):
        material = make_material("Ko'zgu 60×80")
        url = reverse("inventory:material_edit", args=[material.pk])
        self.client.post(url, {
            "name": material.name, "category": OTHER_CATEGORY, "new_category": "Oyna", "unit_of_measure": MeasurementUnit.PIECE,
            "minimum_threshold": "0", "allowed_roles": [UserRole.SBORKACHI], "is_active": "on",
        })
        material.refresh_from_db()
        self.assertEqual(material.category, "OYNA")
        self.assertTrue(Category.objects.filter(code="OYNA", name="Oyna").exists())
