using UnityEngine;
using UnityEngine.UI;

namespace BallGame.Pinball
{
    public sealed class PinballGameController : MonoBehaviour
    {
        public static PinballGameController Instance { get; private set; }

        [SerializeField] private int startingBalls = 3;
        [SerializeField] private Transform ballSpawn;
        [SerializeField] private Text scoreText;
        [SerializeField] private Text ballsText;
        [SerializeField] private Text statusText;

        private Rigidbody2D activeBall;
        private int ballsRemaining;
        private int score;

        public Rigidbody2D ActiveBall => activeBall;

        public void Configure(Transform spawnPoint, Text scoreLabel, Text ballsLabel, Text statusLabel, int ballCount)
        {
            ballSpawn = spawnPoint;
            scoreText = scoreLabel;
            ballsText = ballsLabel;
            statusText = statusLabel;
            startingBalls = Mathf.Max(1, ballCount);
            ballsRemaining = startingBalls;
        }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }

            Instance = this;
            ballsRemaining = Mathf.Max(1, startingBalls);
        }

        private void Start()
        {
            ResetBall();
            UpdateHud();
        }

        public void RegisterBall(Rigidbody2D ball)
        {
            activeBall = ball;
            ResetBall();
            UpdateHud();
        }

        public void AddScore(int amount)
        {
            score += Mathf.Max(0, amount);
            UpdateHud();
        }

        public void DrainBall()
        {
            ballsRemaining--;

            if (ballsRemaining <= 0)
            {
                ballsRemaining = startingBalls;
                score = 0;
                SetStatus("Game Over - score reset");
            }
            else
            {
                SetStatus("Ball drained");
            }

            ResetBall();
            UpdateHud();
        }

        public void SetStatus(string message)
        {
            if (statusText != null)
            {
                statusText.text = message;
            }
        }

        private void ResetBall()
        {
            if (activeBall == null || ballSpawn == null)
            {
                return;
            }

            activeBall.velocity = Vector2.zero;
            activeBall.angularVelocity = 0f;
            activeBall.position = ballSpawn.position;
            activeBall.rotation = 0f;
            activeBall.Sleep();
        }

        private void UpdateHud()
        {
            if (scoreText != null)
            {
                scoreText.text = $"Score: {score}";
            }

            if (ballsText != null)
            {
                ballsText.text = $"Balls: {ballsRemaining}";
            }
        }
    }
}
