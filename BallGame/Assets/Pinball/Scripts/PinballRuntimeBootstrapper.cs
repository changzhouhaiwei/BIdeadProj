using UnityEngine;
using UnityEngine.UI;

namespace BallGame.Pinball
{
    public sealed class PinballRuntimeBootstrapper : MonoBehaviour
    {
        private const string RootName = "Runtime Pinball Table";

        private Sprite squareSprite;
        private Sprite circleSprite;
        private PhysicsMaterial2D ballMaterial;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void CreateTableOnPlay()
        {
            if (FindObjectOfType<PinballGameController>() != null || FindObjectOfType<PinballSceneMarker>() != null)
            {
                return;
            }

            GameObject root = new GameObject(RootName);
            root.AddComponent<PinballRuntimeBootstrapper>().Build();
        }

        private void Build()
        {
            squareSprite = CreateSprite("Pinball Square", false);
            circleSprite = CreateSprite("Pinball Circle", true);
            ballMaterial = new PhysicsMaterial2D("Pinball Ball Material")
            {
                bounciness = 0.55f,
                friction = 0.05f
            };

            Camera camera = EnsureCamera();
            Text scoreText;
            Text ballsText;
            Text statusText;
            CreateHud(camera, out scoreText, out ballsText, out statusText);

            Transform spawn = CreateMarker("Ball Spawn", new Vector2(2.65f, -3.35f));
            PinballGameController controller = gameObject.AddComponent<PinballGameController>();
            controller.Configure(spawn, scoreText, ballsText, statusText, 3);

            CreateStaticTable();
            CreateBumpers();
            CreateFlippers();
            CreatePlunger();
            CreateBall(spawn.position);
        }

        private Camera EnsureCamera()
        {
            Camera camera = Camera.main;
            if (camera == null)
            {
                GameObject cameraObject = new GameObject("Main Camera");
                cameraObject.tag = "MainCamera";
                camera = cameraObject.AddComponent<Camera>();
            }

            camera.orthographic = true;
            camera.orthographicSize = 4.8f;
            camera.transform.position = new Vector3(0f, 0f, -10f);
            camera.backgroundColor = new Color(0.04f, 0.05f, 0.08f);
            return camera;
        }

        private void CreateHud(Camera camera, out Text scoreText, out Text ballsText, out Text statusText)
        {
            GameObject canvasObject = new GameObject("Pinball HUD");
            canvasObject.transform.SetParent(transform);

            Canvas canvas = canvasObject.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasObject.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasObject.AddComponent<GraphicRaycaster>();

            scoreText = CreateText(canvasObject.transform, "Score Text", new Vector2(18f, -18f), "Score: 0");
            ballsText = CreateText(canvasObject.transform, "Balls Text", new Vector2(18f, -46f), "Balls: 3");
            statusText = CreateText(canvasObject.transform, "Status Text", new Vector2(18f, -74f), "Space: charge launch  |  A/D or arrows: flippers");
        }

        private Text CreateText(Transform parent, string name, Vector2 anchoredPosition, string text)
        {
            GameObject textObject = new GameObject(name);
            textObject.transform.SetParent(parent, false);

            Text label = textObject.AddComponent<Text>();
            label.font = Resources.GetBuiltinResource<Font>("Arial.ttf");
            label.fontSize = 18;
            label.color = Color.white;
            label.alignment = TextAnchor.MiddleLeft;
            label.text = text;

            RectTransform rect = label.rectTransform;
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(0f, 1f);
            rect.pivot = new Vector2(0f, 1f);
            rect.anchoredPosition = anchoredPosition;
            rect.sizeDelta = new Vector2(560f, 26f);
            return label;
        }

        private void CreateStaticTable()
        {
            CreateBox("Left Wall", new Vector2(-3.1f, 0f), new Vector2(0.22f, 7.8f), 0f, new Color(0.18f, 0.36f, 0.85f));
            CreateBox("Right Wall", new Vector2(3.1f, 0f), new Vector2(0.22f, 7.8f), 0f, new Color(0.18f, 0.36f, 0.85f));
            CreateBox("Top Wall", new Vector2(0f, 3.8f), new Vector2(6.2f, 0.22f), 0f, new Color(0.18f, 0.36f, 0.85f));
            CreateBox("Launch Lane Divider", new Vector2(2.15f, -0.35f), new Vector2(0.14f, 6.1f), 0f, new Color(0.18f, 0.36f, 0.85f));
            CreateBox("Top Deflector", new Vector2(2.55f, 3.25f), new Vector2(1.1f, 0.18f), -35f, new Color(0.85f, 0.4f, 0.16f));

            CreateBox("Left Outlane", new Vector2(-2.05f, -2.75f), new Vector2(1.8f, 0.18f), 28f, new Color(0.85f, 0.4f, 0.16f));
            CreateBox("Right Outlane", new Vector2(1.05f, -2.75f), new Vector2(1.8f, 0.18f), -28f, new Color(0.85f, 0.4f, 0.16f));
            CreateBox("Left Lower Wall", new Vector2(-2.95f, -3.4f), new Vector2(0.22f, 1.05f), 0f, new Color(0.18f, 0.36f, 0.85f));
            CreateBox("Right Lower Wall", new Vector2(2.95f, -3.4f), new Vector2(0.22f, 1.05f), 0f, new Color(0.18f, 0.36f, 0.85f));

            GameObject loseZone = CreateBox("Lose Zone", new Vector2(0f, -4.15f), new Vector2(5.7f, 0.35f), 0f, new Color(0.35f, 0.05f, 0.08f), true);
            loseZone.AddComponent<PinballLoseZone>();
        }

        private void CreateBumpers()
        {
            CreateBumper("Top Bumper", new Vector2(-0.8f, 1.8f), 150, new Color(1f, 0.32f, 0.35f));
            CreateBumper("Left Bumper", new Vector2(-1.55f, 0.35f), 100, new Color(1f, 0.85f, 0.28f));
            CreateBumper("Right Bumper", new Vector2(0.65f, 0.55f), 100, new Color(0.35f, 0.95f, 1f));
            CreateBumper("Lower Bumper", new Vector2(-0.25f, -1.2f), 200, new Color(0.75f, 0.5f, 1f));
        }

        private void CreateFlippers()
        {
            GameObject left = CreateBox("Left Flipper", new Vector2(-0.9f, -3.35f), new Vector2(1.35f, 0.22f), -22f, new Color(0.9f, 0.9f, 0.95f));
            left.AddComponent<Rigidbody2D>();
            left.AddComponent<PinballFlipper>().Configure(KeyCode.A, KeyCode.LeftArrow, -22f, 36f);

            GameObject right = CreateBox("Right Flipper", new Vector2(0.9f, -3.35f), new Vector2(1.35f, 0.22f), 22f, new Color(0.9f, 0.9f, 0.95f));
            right.AddComponent<Rigidbody2D>();
            right.AddComponent<PinballFlipper>().Configure(KeyCode.D, KeyCode.RightArrow, 22f, -36f);
        }

        private void CreatePlunger()
        {
            GameObject trigger = CreateBox("Plunger Trigger", new Vector2(2.65f, -3.25f), new Vector2(0.7f, 1.4f), 0f, new Color(0.15f, 0.7f, 0.25f), true);
            GameObject visual = CreateBox("Plunger Visual", new Vector2(2.65f, -4.0f), new Vector2(0.55f, 0.16f), 0f, new Color(0.95f, 0.95f, 0.55f));
            trigger.AddComponent<PinballPlunger>().Configure(visual.transform, Vector2.up, 7f, 25f);
        }

        private void CreateBall(Vector3 position)
        {
            GameObject ball = new GameObject("Pinball");
            ball.transform.SetParent(transform);
            ball.transform.position = position;
            ball.transform.localScale = Vector3.one * 0.35f;

            SpriteRenderer renderer = ball.AddComponent<SpriteRenderer>();
            renderer.sprite = circleSprite;
            renderer.color = new Color(0.95f, 0.95f, 1f);
            renderer.sortingOrder = 10;

            CircleCollider2D collider = ball.AddComponent<CircleCollider2D>();
            collider.sharedMaterial = ballMaterial;

            Rigidbody2D body = ball.AddComponent<Rigidbody2D>();
            body.gravityScale = 0.95f;
            body.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
            body.interpolation = RigidbodyInterpolation2D.Interpolate;
            body.drag = 0.03f;
            body.angularDrag = 0.05f;

            ball.AddComponent<PinballBall>();
        }

        private GameObject CreateBumper(string name, Vector2 position, int score, Color color)
        {
            GameObject bumper = new GameObject(name);
            bumper.transform.SetParent(transform);
            bumper.transform.position = position;
            bumper.transform.localScale = Vector3.one * 0.72f;

            SpriteRenderer renderer = bumper.AddComponent<SpriteRenderer>();
            renderer.sprite = circleSprite;
            renderer.color = color;
            renderer.sortingOrder = 2;

            CircleCollider2D collider = bumper.AddComponent<CircleCollider2D>();
            collider.radius = 0.5f;

            bumper.AddComponent<PinballBumper>().Configure(score, 8.5f);
            return bumper;
        }

        private GameObject CreateBox(string name, Vector2 position, Vector2 size, float rotation, Color color, bool isTrigger = false)
        {
            GameObject box = new GameObject(name);
            box.transform.SetParent(transform);
            box.transform.position = position;
            box.transform.rotation = Quaternion.Euler(0f, 0f, rotation);
            box.transform.localScale = new Vector3(size.x, size.y, 1f);

            SpriteRenderer renderer = box.AddComponent<SpriteRenderer>();
            renderer.sprite = squareSprite;
            renderer.color = color;
            renderer.sortingOrder = 1;

            BoxCollider2D collider = box.AddComponent<BoxCollider2D>();
            collider.isTrigger = isTrigger;
            return box;
        }

        private Transform CreateMarker(string name, Vector2 position)
        {
            GameObject marker = new GameObject(name);
            marker.transform.SetParent(transform);
            marker.transform.position = position;
            return marker.transform;
        }

        private Sprite CreateSprite(string name, bool circle)
        {
            const int size = 32;
            Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false);
            texture.name = name;
            texture.filterMode = FilterMode.Bilinear;

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
            return Sprite.Create(texture, new Rect(0f, 0f, size, size), new Vector2(0.5f, 0.5f), size);
        }
    }
}
