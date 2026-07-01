using System.IO;
using BallGame.Pinball;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace BallGame.Pinball.Editor
{
    [InitializeOnLoad]
    internal static class PinballSceneAutoBuilder
    {
        static PinballSceneAutoBuilder()
        {
            EditorApplication.delayCall += BuildMissingScene;
        }

        private static void BuildMissingScene()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || File.Exists(PinballSceneBuilder.SceneFilePath))
            {
                return;
            }

            PinballSceneBuilder.BuildPlayableScene();
        }
    }

    public static class PinballSceneBuilder
    {
        private const string ScenePath = "Assets/Scenes/PinballScene.unity";
        private const string GeneratedArtFolder = "Assets/Pinball/GeneratedArt";
        private const string ImportedFolder = "Assets/Pinball/Imported";

        public static string SceneFilePath => ScenePath;

        private static Sprite squareSprite;
        private static Sprite circleSprite;
        private static PhysicsMaterial2D ballPhysicsMaterial;
        private static AudioClip bumperSound;
        private static AudioClip flipperSound;
        private static AudioClip launchSound;
        private static AudioClip plungerStressSound;
        private static AudioClip drainSound;

        [MenuItem("Pinball/Build Playable Scene")]
        public static void BuildPlayableScene()
        {
            EnsureGeneratedArt();
            LoadAssets();

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "PinballScene";

            GameObject root = new GameObject("Pinball Scene");
            root.AddComponent<PinballSceneMarker>();

            Camera camera = CreateCamera(root.transform);
            Text scoreText;
            Text ballsText;
            Text statusText;
            CreateHud(root.transform, out scoreText, out ballsText, out statusText);

            Transform spawn = CreateMarker(root.transform, "Ball Spawn", new Vector2(2.65f, -3.35f));
            PinballGameController controller = root.AddComponent<PinballGameController>();
            controller.Configure(spawn, scoreText, ballsText, statusText, 3);

            CreateTableBackdrop(root.transform);
            CreateStaticTable(root.transform);
            CreateBumpers(root.transform);
            CreateSlingshots(root.transform);
            CreateFlippers(root.transform);
            CreatePlunger(root.transform);
            CreateDropSlots(root.transform);
            CreateBall(root.transform, spawn.position);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"Pinball scene created at {ScenePath}");
        }

        private static void EnsureGeneratedArt()
        {
            Directory.CreateDirectory(GeneratedArtFolder);
            CreateTextureAsset("pinball_square.png", false, new Color(1f, 1f, 1f, 1f));
            CreateTextureAsset("pinball_circle.png", true, new Color(1f, 1f, 1f, 1f));
            AssetDatabase.Refresh();
            ConfigureSpriteImport(Path.Combine(GeneratedArtFolder, "pinball_square.png").Replace("\\", "/"));
            ConfigureSpriteImport(Path.Combine(GeneratedArtFolder, "pinball_circle.png").Replace("\\", "/"));
            AssetDatabase.Refresh();
        }

        private static void CreateTextureAsset(string fileName, bool circle, Color color)
        {
            string path = Path.Combine(GeneratedArtFolder, fileName);
            if (File.Exists(path))
            {
                return;
            }

            const int size = 64;
            Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false);
            Vector2 center = new Vector2((size - 1) * 0.5f, (size - 1) * 0.5f);
            float radius = (size - 1) * 0.48f;

            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    bool opaque = !circle || Vector2.Distance(new Vector2(x, y), center) <= radius;
                    texture.SetPixel(x, y, opaque ? color : Color.clear);
                }
            }

            texture.Apply();
            File.WriteAllBytes(path, texture.EncodeToPNG());
            Object.DestroyImmediate(texture);
        }

        private static void ConfigureSpriteImport(string path)
        {
            TextureImporter importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null)
            {
                return;
            }

            importer.textureType = TextureImporterType.Sprite;
            importer.spritePixelsPerUnit = 64f;
            importer.mipmapEnabled = false;
            importer.alphaIsTransparency = true;
            importer.SaveAndReimport();
        }

        private static void LoadAssets()
        {
            squareSprite = AssetDatabase.LoadAssetAtPath<Sprite>($"{GeneratedArtFolder}/pinball_square.png");
            circleSprite = AssetDatabase.LoadAssetAtPath<Sprite>($"{GeneratedArtFolder}/pinball_circle.png");
            bumperSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/bumper.wav");
            flipperSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/flipper.wav");
            launchSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/launch.wav");
            plungerStressSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/plunger-stress.wav");
            drainSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/death.wav");

            ballPhysicsMaterial = new PhysicsMaterial2D("Pinball Ball 2D Material")
            {
                bounciness = 0.58f,
                friction = 0.03f
            };
        }

        private static Camera CreateCamera(Transform parent)
        {
            GameObject cameraObject = new GameObject("Main Camera");
            cameraObject.transform.SetParent(parent);
            cameraObject.tag = "MainCamera";
            cameraObject.transform.position = new Vector3(0f, 0f, -10f);

            Camera camera = cameraObject.AddComponent<Camera>();
            camera.orthographic = true;
            camera.orthographicSize = 4.8f;
            camera.backgroundColor = new Color(0.025f, 0.03f, 0.06f);
            return camera;
        }

        private static void CreateHud(Transform parent, out Text scoreText, out Text ballsText, out Text statusText)
        {
            GameObject canvasObject = new GameObject("Pinball HUD");
            canvasObject.transform.SetParent(parent);

            Canvas canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            CanvasScaler scaler = canvasObject.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1080f, 1920f);
            canvasObject.AddComponent<GraphicRaycaster>();

            scoreText = CreateText(canvasObject.transform, "Score Text", new Vector2(22f, -22f), "Score: 0", 30);
            ballsText = CreateText(canvasObject.transform, "Balls Text", new Vector2(22f, -62f), "Balls: 3", 24);
            statusText = CreateText(canvasObject.transform, "Status Text", new Vector2(22f, -98f), "Space: charge launch  |  A/D or arrows: flippers", 20);
        }

        private static Text CreateText(Transform parent, string name, Vector2 anchoredPosition, string text, int fontSize)
        {
            GameObject textObject = new GameObject(name);
            textObject.transform.SetParent(parent, false);

            Text label = textObject.AddComponent<Text>();
            label.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            label.fontSize = fontSize;
            label.color = Color.white;
            label.alignment = TextAnchor.MiddleLeft;
            label.text = text;

            RectTransform rect = label.rectTransform;
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = anchoredPosition;
            rect.sizeDelta = new Vector2(760f, 40f);
            return label;
        }

        private static void CreateTableBackdrop(Transform parent)
        {
            CreateBox(parent, "Neon Backboard", new Vector2(0f, -0.15f), new Vector2(6.5f, 8.25f), 0f, new Color(0.055f, 0.065f, 0.13f), 0);
            CreateBox(parent, "Playfield Glow", new Vector2(-0.2f, -0.1f), new Vector2(4.4f, 7.2f), 0f, new Color(0.09f, 0.1f, 0.18f), 0);
            CreateBox(parent, "Launch Lane Glow", new Vector2(2.63f, -0.35f), new Vector2(0.78f, 6.8f), 0f, new Color(0.08f, 0.16f, 0.18f), 0);
        }

        private static void CreateStaticTable(Transform parent)
        {
            CreateWall(parent, "Left Wall", new Vector2(-3.1f, 0f), new Vector2(0.2f, 7.8f), 0f);
            CreateWall(parent, "Right Wall", new Vector2(3.1f, 0f), new Vector2(0.2f, 7.8f), 0f);
            CreateWall(parent, "Top Wall", new Vector2(0f, 3.8f), new Vector2(6.2f, 0.2f), 0f);
            CreateWall(parent, "Launch Lane Divider", new Vector2(2.15f, -0.35f), new Vector2(0.14f, 6.1f), 0f);
            CreateBox(parent, "Top Deflector", new Vector2(2.56f, 3.22f), new Vector2(1.15f, 0.18f), -35f, new Color(1f, 0.44f, 0.16f), 4);
            CreateBox(parent, "Left Guide", new Vector2(-2.05f, -2.75f), new Vector2(1.8f, 0.18f), 28f, new Color(1f, 0.44f, 0.16f), 4);
            CreateBox(parent, "Right Guide", new Vector2(1.05f, -2.75f), new Vector2(1.8f, 0.18f), -28f, new Color(1f, 0.44f, 0.16f), 4);

            GameObject loseZone = CreateBox(parent, "Lose Zone", new Vector2(0f, -4.55f), new Vector2(5.7f, 0.28f), 0f, new Color(0.3f, 0.02f, 0.05f), 3, true);
            loseZone.AddComponent<AudioSource>();
            loseZone.AddComponent<PinballLoseZone>().Configure(drainSound);
        }

        private static void CreateWall(Transform parent, string name, Vector2 position, Vector2 size, float rotation)
        {
            CreateBox(parent, name, position, size, rotation, new Color(0.14f, 0.48f, 1f), 5);
            CreateBox(parent, $"{name} Glow", position, size + new Vector2(0.08f, 0.08f), rotation, new Color(0.03f, 0.15f, 0.3f), 2);
        }

        private static void CreateBumpers(Transform parent)
        {
            CreateBumper(parent, "Top Bumper", new Vector2(-0.8f, 1.75f), 150, new Color(1f, 0.32f, 0.36f));
            CreateBumper(parent, "Left Bumper", new Vector2(-1.55f, 0.35f), 100, new Color(1f, 0.86f, 0.2f));
            CreateBumper(parent, "Right Bumper", new Vector2(0.65f, 0.55f), 100, new Color(0.28f, 0.95f, 1f));
            CreateBumper(parent, "Lower Bumper", new Vector2(-0.2f, -1.25f), 200, new Color(0.72f, 0.46f, 1f));
        }

        private static void CreateBumper(Transform parent, string name, Vector2 position, int score, Color color)
        {
            GameObject bumper = CreateCircle(parent, name, position, 0.78f, color, 8);
            bumper.AddComponent<CircleCollider2D>();
            bumper.AddComponent<AudioSource>();
            bumper.AddComponent<PinballBumper>().Configure(score, 8.5f, bumperSound);
            CreateCircle(parent, $"{name} Halo", position, 1.05f, new Color(color.r * 0.35f, color.g * 0.35f, color.b * 0.35f, 0.9f), 3);
        }

        private static void CreateSlingshots(Transform parent)
        {
            GameObject left = CreateBox(parent, "Left Slingshot", new Vector2(-1.95f, -2.1f), new Vector2(0.8f, 0.2f), 36f, new Color(0.25f, 1f, 0.55f), 6);
            left.AddComponent<PinballBumper>().Configure(60, 6f, bumperSound);

            GameObject right = CreateBox(parent, "Right Slingshot", new Vector2(0.95f, -2.1f), new Vector2(0.8f, 0.2f), -36f, new Color(0.25f, 1f, 0.55f), 6);
            right.AddComponent<PinballBumper>().Configure(60, 6f, bumperSound);
        }

        private static void CreateFlippers(Transform parent)
        {
            GameObject left = CreateBox(parent, "Left Flipper", new Vector2(-0.9f, -3.35f), new Vector2(1.35f, 0.24f), -22f, new Color(0.96f, 0.96f, 1f), 9);
            left.AddComponent<Rigidbody2D>();
            left.AddComponent<AudioSource>();
            left.AddComponent<PinballFlipper>().Configure(KeyCode.A, KeyCode.LeftArrow, -22f, 36f, flipperSound);

            GameObject right = CreateBox(parent, "Right Flipper", new Vector2(0.9f, -3.35f), new Vector2(1.35f, 0.24f), 22f, new Color(0.96f, 0.96f, 1f), 9);
            right.AddComponent<Rigidbody2D>();
            right.AddComponent<AudioSource>();
            right.AddComponent<PinballFlipper>().Configure(KeyCode.D, KeyCode.RightArrow, 22f, -36f, flipperSound);
        }

        private static void CreatePlunger(Transform parent)
        {
            GameObject trigger = CreateBox(parent, "Plunger Trigger", new Vector2(2.65f, -3.25f), new Vector2(0.7f, 1.45f), 0f, new Color(0.15f, 0.7f, 0.25f, 0.35f), 4, true);
            GameObject visual = CreateBox(parent, "Plunger Visual", new Vector2(2.65f, -4.0f), new Vector2(0.55f, 0.18f), 0f, new Color(1f, 0.95f, 0.35f), 10);
            trigger.AddComponent<AudioSource>();
            trigger.AddComponent<PinballPlunger>().Configure(visual.transform, Vector2.up, 7f, 25f, plungerStressSound, launchSound);
        }

        private static void CreateDropSlots(Transform parent)
        {
            GameObject root = new GameObject("Drop Slot Rewards");
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
                GameObject slotVisual = CreateBox(root.transform, $"Drop Slot {i + 1} Visual", new Vector2(x, slotY), new Vector2(slotWidth, 0.24f), 0f, new Color(0.08f, 0.08f, 0.11f), 6);
                slotVisual.GetComponent<Collider2D>().enabled = false;
                SpriteRenderer slotRenderer = slotVisual.GetComponent<SpriteRenderer>();

                GameObject trigger = CreateBox(root.transform, $"Drop Slot {i + 1}", new Vector2(x, slotY), new Vector2(slotWidth, 0.34f), 0f, new Color(1f, 1f, 1f, 0f), 1, true);
                GameObject light = CreateCircle(root.transform, $"Drop Slot {i + 1} Red Light", new Vector2(x, lightY), 0.24f, new Color(0.18f, 0.02f, 0.025f), 11);

                PinballDropSlot slot = trigger.AddComponent<PinballDropSlot>();
                slot.Configure(controller, light.GetComponent<SpriteRenderer>(), slotRenderer, new Color(1f, 0.08f, 0.05f), new Color(0.18f, 0.02f, 0.025f));
                controller.RegisterSlot(slot);
            }

            for (int i = 0; i <= slotCount; i++)
            {
                float x = leftEdge + cellWidth * i;
                CreateBox(root.transform, $"Drop Slot Divider {i}", new Vector2(x, slotY + 0.04f), new Vector2(dividerWidth, 0.62f), 0f, new Color(0.14f, 0.48f, 1f), 7);
            }
        }

        private static void CreateBall(Transform parent, Vector3 position)
        {
            GameObject ball = CreateCircle(parent, "Pinball", position, 0.36f, new Color(0.92f, 0.94f, 1f), 12);
            CircleCollider2D collider = ball.AddComponent<CircleCollider2D>();
            collider.sharedMaterial = ballPhysicsMaterial;

            Rigidbody2D body = ball.AddComponent<Rigidbody2D>();
            body.gravityScale = 0.95f;
            body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            body.drag = 0.03f;
            body.angularDrag = 0.05f;

            ball.AddComponent<PinballBall>();
        }

        private static GameObject CreateBox(Transform parent, string name, Vector2 position, Vector2 size, float rotation, Color color, int sortingOrder, bool isTrigger = false)
        {
            GameObject box = new GameObject(name);
            box.transform.SetParent(parent);
            box.transform.position = position;
            box.transform.rotation = Quaternion.Euler(0f, 0f, rotation);
            box.transform.localScale = new Vector3(size.x, size.y, 1f);

            SpriteRenderer renderer = box.AddComponent<SpriteRenderer>();
            renderer.sprite = squareSprite;
            renderer.color = color;
            renderer.sortingOrder = sortingOrder;

            BoxCollider2D collider = box.AddComponent<BoxCollider2D>();
            collider.isTrigger = isTrigger;
            return box;
        }

        private static GameObject CreateCircle(Transform parent, string name, Vector2 position, float size, Color color, int sortingOrder)
        {
            GameObject circle = new GameObject(name);
            circle.transform.SetParent(parent);
            circle.transform.position = position;
            circle.transform.localScale = Vector3.one * size;

            SpriteRenderer renderer = circle.AddComponent<SpriteRenderer>();
            renderer.sprite = circleSprite;
            renderer.color = color;
            renderer.sortingOrder = sortingOrder;
            return circle;
        }

        private static Transform CreateMarker(Transform parent, string name, Vector2 position)
        {
            GameObject marker = new GameObject(name);
            marker.transform.SetParent(parent);
            marker.transform.position = position;
            return marker.transform;
        }
    }
}
