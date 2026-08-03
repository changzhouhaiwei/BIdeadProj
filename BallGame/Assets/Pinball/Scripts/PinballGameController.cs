using UnityEngine;
using UnityEngine.UI;

namespace BallGame.Pinball
{
    public sealed class PinballGameController : MonoBehaviour
    {
        public static PinballGameController Instance { get; private set; }

        [SerializeField] private int startingBalls;
        [SerializeField] private Transform ballSpawn;
        [SerializeField] private Text scoreText;
        [SerializeField] private Text ballsText;
        [SerializeField] private Text statusText;
        [SerializeField] private Text inventoryText;
        [SerializeField] private Text resultText;
        [SerializeField] private Button startButton;
        [SerializeField] private Button restartButton;
        [SerializeField] private Button coinButton;

        private Rigidbody2D activeBall;
        private PinballDropSlotRewardController dropSlotRewardController;
        private int ballsRemaining;
        private int score;
        private int roundAwardedBalls;
        private bool roundInProgress;
        private bool configured;

        public Rigidbody2D ActiveBall => activeBall;
        public bool IsRoundInProgress => roundInProgress;

        public void Configure(
            Transform spawnPoint,
            Text scoreLabel,
            Text ballsLabel,
            Text statusLabel,
            Text inventoryLabel,
            Text resultLabel,
            Button startGameButton,
            Button restartGameButton,
            Button simulateCoinButton,
            int ballCount)
        {
            ballSpawn = spawnPoint;
            scoreText = scoreLabel;
            ballsText = ballsLabel;
            statusText = statusLabel;
            inventoryText = inventoryLabel;
            resultText = resultLabel;
            startButton = startGameButton;
            restartButton = restartGameButton;
            coinButton = simulateCoinButton;
            startingBalls = Mathf.Max(0, ballCount);
            ballsRemaining = startingBalls;
            configured = true;
            HookButtons();
            UpdateHud();
        }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }

            Instance = this;
            if (!configured)
            {
                ballsRemaining = Mathf.Max(0, startingBalls);
            }

            HookButtons();
        }

        private void Start()
        {
            ParkBall();
            SetStatus("Insert a coin to add a ball");
            SetResult("No ball inserted");
            UpdateHud();
        }

        public void RegisterBall(Rigidbody2D ball)
        {
            activeBall = ball;
            ParkBall();
            UpdateHud();
        }

        public void AddScore(int amount)
        {
            score += Mathf.Max(0, amount);
            UpdateHud();
        }

        public void AddBalls(int amount)
        {
            ballsRemaining += Mathf.Max(0, amount);
            UpdateHud();
        }

        public void AwardBonusBalls(int amount)
        {
            int reward = Mathf.Max(0, amount);
            roundAwardedBalls += reward;
            AddBalls(reward);
            SetStatus($"Reward slot hit +{reward} balls");
        }

        public void RegisterDropSlotRewardController(PinballDropSlotRewardController controller)
        {
            dropSlotRewardController = controller;
        }

        public void SimulateCoin()
        {
            ballsRemaining++;
            SetStatus("Coin inserted +1 ball");
            if (!roundInProgress)
            {
                SetResult("Ready to start");
            }

            UpdateHud();
        }

        public void StartGame()
        {
            if (roundInProgress)
            {
                SetStatus("Ball is already in play");
                return;
            }

            if (ballsRemaining <= 0)
            {
                SetStatus("Insert a coin first");
                SetResult("No balls remaining");
                UpdateHud();
                return;
            }

            ballsRemaining--;
            roundAwardedBalls = 0;
            roundInProgress = true;
            SetStatus("Game started");
            SetResult("Ball in play");
            ResetBallForRound();
            UpdateHud();
        }

        public void RestartGame()
        {
            score = 0;
            ballsRemaining = Mathf.Max(0, startingBalls);
            roundAwardedBalls = 0;
            roundInProgress = false;
            ParkBall();
            SetStatus("Game reset");
            SetResult(ballsRemaining > 0 ? "Ready to start" : "No ball inserted");
            UpdateHud();
        }

        public void DrainBall(string statusMessage = null)
        {
            if (!roundInProgress)
            {
                ParkBall();
                UpdateHud();
                return;
            }

            roundInProgress = false;
            if (!string.IsNullOrEmpty(statusMessage))
            {
                SetStatus(statusMessage);
            }
            else
            {
                SetStatus("Ball drained");
            }

            SetResult(roundAwardedBalls > 0
                ? $"You won {roundAwardedBalls} balls"
                : "No reward this round");
            ParkBall();
            UpdateHud();
        }

        public void SetStatus(string message)
        {
            if (statusText != null)
            {
                statusText.text = message;
            }
        }

        private void SetResult(string message)
        {
            if (resultText != null)
            {
                resultText.text = message;
            }
        }

        private void ResetBallForRound()
        {
            if (activeBall == null || ballSpawn == null)
            {
                return;
            }

            activeBall.simulated = true;
            activeBall.gravityScale = 0f;
            activeBall.velocity = Vector2.zero;
            activeBall.angularVelocity = 0f;
            activeBall.position = ballSpawn.position;
            activeBall.rotation = 0f;
            activeBall.Sleep();
            dropSlotRewardController?.StartNewRound();
        }

        private void ParkBall()
        {
            if (activeBall == null)
            {
                return;
            }

            activeBall.velocity = Vector2.zero;
            activeBall.angularVelocity = 0f;
            if (ballSpawn != null)
            {
                activeBall.position = ballSpawn.position;
                activeBall.rotation = 0f;
            }

            activeBall.Sleep();
            activeBall.simulated = false;
        }

        private void HookButtons()
        {
            if (startButton != null)
            {
                startButton.onClick.RemoveListener(StartGame);
                startButton.onClick.AddListener(StartGame);
            }

            if (restartButton != null)
            {
                restartButton.onClick.RemoveListener(RestartGame);
                restartButton.onClick.AddListener(RestartGame);
            }

            if (coinButton != null)
            {
                coinButton.onClick.RemoveListener(SimulateCoin);
                coinButton.onClick.AddListener(SimulateCoin);
            }
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

            if (inventoryText != null)
            {
                inventoryText.text = $"Remaining Balls: {ballsRemaining}";
            }

            if (startButton != null)
            {
                startButton.interactable = ballsRemaining > 0 && !roundInProgress;
            }

            if (coinButton != null)
            {
                coinButton.interactable = true;
            }
        }
    }
}
