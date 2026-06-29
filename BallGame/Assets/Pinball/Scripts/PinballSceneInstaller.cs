using UnityEngine;
using UnityEngine.UI;

#if UNITY_EDITOR
using UnityEditor;
#endif

namespace BallGame.Pinball
{
    [ExecuteAlways]
    public sealed class PinballSceneInstaller : MonoBehaviour
    {
        private const string GeneratedRootName = "Generated Pinball Table";
        private const string ImportedFolder = "Assets/Pinball/Imported";

        private Sprite squareSprite;
        private Sprite circleSprite;
        private AudioClip bumperSound;
        private AudioClip flipperSound;
        private AudioClip launchSound;
        private AudioClip stressSound;
        private AudioClip drainSound;
        private bool builtThisPlaySession;

        private void OnEnable()
        {
            EnsureInstalled();
        }

        private void Start()
        {
            EnsureInstalled();
        }

        private void EnsureInstalled()
        {
            if (Application.isPlaying && builtThisPlaySession)
            {
                return;
            }

            Transform existing = transform.Find(GeneratedRootName);
            if (existing != null && !Application.isPlaying && IsCompleteTable(existing))
            {
                return;
            }

            if (existing != null)
            {
                RemoveExistingTable(existing);
            }

            LoadImportedFeedback();
            BuildSceneObjects();
            builtThisPlaySession = Application.isPlaying;
        }

        [ContextMenu("Rebuild Pinball Table")]
        public void Rebuild()
        {
            Transform existing = transform.Find(GeneratedRootName);
            if (existing != null)
            {
                RemoveExistingTable(existing);
            }

            LoadImportedFeedback();
            BuildSceneObjects();
        }

        private bool IsCompleteTable(Transform table)
        {
            return table.Find("Pinball HUD") != null
                && table.Find("Neon Backboard") != null
                && table.Find("Left Flipper") != null
                && table.Find("Right Flipper") != null
                && table.Find("Plunger Trigger") != null
                && table.Find("Pinball") != null
                && HasValidSprite(table.Find("Pinball"))
                && HasValidSprite(table.Find("Neon Backboard"));
        }

        private bool HasValidSprite(Transform target)
        {
            if (target == null)
            {
                return false;
            }

            SpriteRenderer renderer = target.GetComponent<SpriteRenderer>();
            return renderer != null && renderer.sprite != null;
        }

        private void RemoveExistingTable(Transform existing)
        {
            if (Application.isPlaying)
            {
                Destroy(existing.gameObject);
            }
            else
            {
                DestroyImmediate(existing.gameObject);
            }
        }

        private void LoadImportedFeedback()
        {
            squareSprite = CreateSprite(false);
            circleSprite = CreateSprite(true);

#if UNITY_EDITOR
            bumperSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/bumper.wav");
            flipperSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/flipper.wav");
            launchSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/launch.wav");
            stressSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/plunger-stress.wav");
            drainSound = AssetDatabase.LoadAssetAtPath<AudioClip>($"{ImportedFolder}/Sounds/death.wav");
#endif
        }

        private void BuildSceneObjects()
        {
            GameObject table = new GameObject(GeneratedRootName);
            table.transform.SetParent(transform);

            Camera camera = Camera.main != null ? Camera.main : CreateCamera(table.transform);
            ConfigureCamera(camera);

            Text scoreText;
            Text ballsText;
            Text statusText;
            CreateHud(table.transform, out scoreText, out ballsText, out statusText);

            Transform spawn = CreateMarker(table.transform, "Ball Spawn", new Vector2(2.65f, -3.35f));
            PinballGameController controller = gameObject.GetComponent<PinballGameController>();
            if (controller == null)
            {
                controller = gameObject.AddComponent<PinballGameController>();
            }

            controller.Configure(spawn, scoreText, ballsText, statusText, 3);

            CreateBackdrop(table.transform);
            CreateStaticTable(table.transform);
            CreateBumpers(table.transform);
            CreateFlippers(table.transform);
            CreatePlunger(table.transform);
            CreateBall(table.transform, spawn.position);
        }

        private Camera CreateCamera(Transform parent)
        {
            GameObject cameraObject = new GameObject("Main Camera");
            cameraObject.transform.SetParent(parent);
            cameraObject.tag = "MainCamera";
            cameraObject.AddComponent<AudioListener>();
            return cameraObject.AddComponent<Camera>();
        }

        private void ConfigureCamera(Camera camera)
        {
            camera.orthographic = true;
            camera.orthographicSize = 4.8f;
            camera.transform.position = new Vector3(0f, 0f, -10f);
            camera.backgroundColor = new Color(0.025f, 0.03f, 0.06f);
        }

        private void CreateHud(Transform parent, out Text scoreText, out Text ballsText, out Text statusText)
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

        private Text CreateText(Transform parent, string name, Vector2 anchoredPosition, string text, int fontSize)
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

        private void CreateBackdrop(Transform parent)
        {
            CreateBox(parent, "Neon Backboard", new Vector2(0f, -0.15f), new Vector2(6.5f, 8.25f), 0f, new Color(0.055f, 0.065f, 0.13f), 0);
            CreateBox(parent, "Playfield Glow", new Vector2(-0.2f, -0.1f), new Vector2(4.4f, 7.2f), 0f, new Color(0.09f, 0.1f, 0.18f), 0);
            CreateBox(parent, "Launch Lane Glow", new Vector2(2.63f, -0.35f), new Vector2(0.78f, 6.8f), 0f, new Color(0.08f, 0.16f, 0.18f), 0);
        }

        private void CreateStaticTable(Transform parent)
        {
            CreateWall(parent, "Left Wall", new Vector2(-3.1f, 0f), new Vector2(0.2f, 7.8f), 0f);
            CreateWall(parent, "Right Wall", new Vector2(3.1f, 0f), new Vector2(0.2f, 7.8f), 0f);
            CreateWall(parent, "Top Wall", new Vector2(0f, 3.8f), new Vector2(6.2f, 0.2f), 0f);
            CreateWall(parent, "Launch Lane Divider", new Vector2(2.15f, -0.35f), new Vector2(0.14f, 6.1f), 0f);
            CreateBox(parent, "Top Deflector", new Vector2(2.56f, 3.22f), new Vector2(1.15f, 0.18f), -35f, new Color(1f, 0.44f, 0.16f), 4);
            CreateBox(parent, "Left Guide", new Vector2(-2.05f, -2.75f), new Vector2(1.8f, 0.18f), 28f, new Color(1f, 0.44f, 0.16f), 4);
            CreateBox(parent, "Right Guide", new Vector2(1.05f, -2.75f), new Vector2(1.8f, 0.18f), -28f, new Color(1f, 0.44f, 0.16f), 4);

            GameObject loseZone = CreateBox(parent, "Lose Zone", new Vector2(0f, -4.15f), new Vector2(5.7f, 0.35f), 0f, new Color(0.3f, 0.02f, 0.05f), 3, true);
            loseZone.AddComponent<AudioSource>();
            loseZone.AddComponent<PinballLoseZone>().Configure(drainSound);
        }

        private void CreateWall(Transform parent, string name, Vector2 position, Vector2 size, float rotation)
        {
            CreateBox(parent, name, position, size, rotation, new Color(0.14f, 0.48f, 1f), 5);
            CreateBox(parent, $"{name} Glow", position, size + new Vector2(0.08f, 0.08f), rotation, new Color(0.03f, 0.15f, 0.3f), 2);
        }

        private void CreateBumpers(Transform parent)
        {
            CreateBumper(parent, "Top Bumper", new Vector2(-0.8f, 1.75f), 150, new Color(1f, 0.32f, 0.36f));
            CreateBumper(parent, "Left Bumper", new Vector2(-1.55f, 0.35f), 100, new Color(1f, 0.86f, 0.2f));
            CreateBumper(parent, "Right Bumper", new Vector2(0.65f, 0.55f), 100, new Color(0.28f, 0.95f, 1f));
            CreateBumper(parent, "Lower Bumper", new Vector2(-0.2f, -1.25f), 200, new Color(0.72f, 0.46f, 1f));
        }

        private void CreateBumper(Transform parent, string name, Vector2 position, int score, Color color)
        {
            CreateCircle(parent, $"{name} Halo", position, 1.05f, new Color(color.r * 0.35f, color.g * 0.35f, color.b * 0.35f, 0.9f), 3);
            GameObject bumper = CreateCircle(parent, name, position, 0.78f, color, 8);
            bumper.AddComponent<CircleCollider2D>();
            bumper.AddComponent<AudioSource>();
            bumper.AddComponent<PinballBumper>().Configure(score, 8.5f, bumperSound);
        }

        private void CreateFlippers(Transform parent)
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

        private void CreatePlunger(Transform parent)
        {
            GameObject trigger = CreateBox(parent, "Plunger Trigger", new Vector2(2.65f, -3.25f), new Vector2(0.7f, 1.45f), 0f, new Color(0.15f, 0.7f, 0.25f, 0.35f), 4, true);
            GameObject visual = CreateBox(parent, "Plunger Visual", new Vector2(2.65f, -4.0f), new Vector2(0.55f, 0.18f), 0f, new Color(1f, 0.95f, 0.35f), 10);
            trigger.AddComponent<AudioSource>();
            trigger.AddComponent<PinballPlunger>().Configure(visual.transform, Vector2.up, 7f, 25f, stressSound, launchSound);
        }

        private void CreateBall(Transform parent, Vector3 position)
        {
            GameObject ball = CreateCircle(parent, "Pinball", position, 0.36f, new Color(0.92f, 0.94f, 1f), 12);
            CircleCollider2D collider = ball.AddComponent<CircleCollider2D>();
            collider.sharedMaterial = new PhysicsMaterial2D("Pinball Ball 2D Material")
            {
                bounciness = 0.58f,
                friction = 0.03f
            };

            Rigidbody2D body = ball.AddComponent<Rigidbody2D>();
            body.gravityScale = 0.95f;
            body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            body.drag = 0.03f;
            body.angularDrag = 0.05f;

            ball.AddComponent<PinballBall>();
        }

        private GameObject CreateBox(Transform parent, string name, Vector2 position, Vector2 size, float rotation, Color color, int sortingOrder, bool isTrigger = false)
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

        private GameObject CreateCircle(Transform parent, string name, Vector2 position, float size, Color color, int sortingOrder)
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

        private Transform CreateMarker(Transform parent, string name, Vector2 position)
        {
            GameObject marker = new GameObject(name);
            marker.transform.SetParent(parent);
            marker.transform.position = position;
            return marker.transform;
        }

        private Sprite CreateSprite(bool circle)
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
