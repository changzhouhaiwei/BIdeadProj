using UnityEngine;

namespace BallGame.Pinball
{
    public sealed class PinballDropSlotSceneBootstrapper : MonoBehaviour
    {
        private const string RootName = "Drop Slot Rewards";

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void EnsureDropSlots()
        {
            EnsureDropSlotsFor(FindObjectOfType<PinballGameController>());
        }

        public static void EnsureDropSlotsFor(PinballGameController gameController)
        {
            if (gameController == null || FindObjectOfType<PinballDropSlotRewardController>() != null)
            {
                return;
            }

            Sprite squareSprite = CreateSprite(false);
            Sprite circleSprite = CreateSprite(true);
            PinballDropSlotRewardController rewardController = CreateDropSlots(gameController.transform, squareSprite, circleSprite);
            gameController.RegisterDropSlotRewardController(rewardController);
            rewardController.StartNewRound();
        }

        private static PinballDropSlotRewardController CreateDropSlots(Transform parent, Sprite squareSprite, Sprite circleSprite)
        {
            GameObject root = new GameObject(RootName);
            root.transform.SetParent(parent);
            PinballDropSlotRewardController controller = root.AddComponent<PinballDropSlotRewardController>();

            const int slotCount = 5;
            const float leftEdge = -2.55f;
            const float rightEdge = 1.75f;
            const float dividerWidth = 0.08f;
            const float slotY = -4.02f;
            const float lightY = -3.66f;
            float cellWidth = (rightEdge - leftEdge) / slotCount;
            float slotWidth = cellWidth - dividerWidth;
            for (int i = 0; i < slotCount; i++)
            {
                float x = leftEdge + cellWidth * (i + 0.5f);
                GameObject slotVisual = CreateBox(root.transform, $"Drop Slot {i + 1} Visual", squareSprite, new Vector2(x, slotY), new Vector2(slotWidth, 0.24f), new Color(0.08f, 0.08f, 0.11f), 6, false);
                slotVisual.GetComponent<Collider2D>().enabled = false;
                SpriteRenderer slotRenderer = slotVisual.GetComponent<SpriteRenderer>();

                GameObject trigger = CreateBox(root.transform, $"Drop Slot {i + 1}", squareSprite, new Vector2(x, slotY), new Vector2(slotWidth, 0.34f), new Color(1f, 1f, 1f, 0f), 1, true);
                GameObject light = CreateCircle(root.transform, $"Drop Slot {i + 1} Red Light", circleSprite, new Vector2(x, lightY), 0.24f, new Color(0.18f, 0.02f, 0.025f), 11);

                PinballDropSlot slot = trigger.AddComponent<PinballDropSlot>();
                slot.Configure(controller, light.GetComponent<SpriteRenderer>(), slotRenderer, new Color(1f, 0.08f, 0.05f), new Color(0.18f, 0.02f, 0.025f));
                controller.RegisterSlot(slot);
            }

            for (int i = 0; i <= slotCount; i++)
            {
                float x = leftEdge + cellWidth * i;
                CreateBox(root.transform, $"Drop Slot Divider {i}", squareSprite, new Vector2(x, slotY + 0.04f), new Vector2(dividerWidth, 0.62f), new Color(0.14f, 0.48f, 1f), 7, false);
            }

            return controller;
        }

        private static GameObject CreateBox(Transform parent, string name, Sprite sprite, Vector2 position, Vector2 size, Color color, int sortingOrder, bool isTrigger)
        {
            GameObject box = new GameObject(name);
            box.transform.SetParent(parent);
            box.transform.position = position;
            box.transform.localScale = new Vector3(size.x, size.y, 1f);

            SpriteRenderer renderer = box.AddComponent<SpriteRenderer>();
            renderer.sprite = sprite;
            renderer.color = color;
            renderer.sortingOrder = sortingOrder;

            BoxCollider2D collider = box.AddComponent<BoxCollider2D>();
            collider.isTrigger = isTrigger;
            return box;
        }

        private static GameObject CreateCircle(Transform parent, string name, Sprite sprite, Vector2 position, float size, Color color, int sortingOrder)
        {
            GameObject circle = new GameObject(name);
            circle.transform.SetParent(parent);
            circle.transform.position = position;
            circle.transform.localScale = Vector3.one * size;

            SpriteRenderer renderer = circle.AddComponent<SpriteRenderer>();
            renderer.sprite = sprite;
            renderer.color = color;
            renderer.sortingOrder = sortingOrder;
            return circle;
        }

        private static Sprite CreateSprite(bool circle)
        {
            const int size = 64;
            Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false)
            {
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Bilinear
            };

            Vector2 center = new Vector2((size - 1) * 0.5f, (size - 1) * 0.5f);
            float radius = (size - 1) * 0.48f;

            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    bool opaque = !circle || Vector2.Distance(new Vector2(x, y), center) <= radius;
                    texture.SetPixel(x, y, opaque ? Color.white : Color.clear);
                }
            }

            texture.Apply();
            Sprite sprite = Sprite.Create(texture, new Rect(0f, 0f, size, size), new Vector2(0.5f, 0.5f), size);
            sprite.hideFlags = HideFlags.HideAndDontSave;
            return sprite;
        }
    }
}
