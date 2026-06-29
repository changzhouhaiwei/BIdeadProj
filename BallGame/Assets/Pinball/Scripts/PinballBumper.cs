using UnityEngine;

namespace BallGame.Pinball
{
    public sealed class PinballBumper : MonoBehaviour
    {
        [SerializeField] private int scoreValue = 100;
        [SerializeField] private float impulse = 8f;
        [SerializeField] private float pulseScale = 1.2f;
        [SerializeField] private float pulseTime = 0.08f;
        [SerializeField] private AudioClip hitSound;

        private AudioSource audioSource;
        private Vector3 baseScale;
        private float pulseTimer;

        public void Configure(int points, float bounceImpulse, AudioClip sound = null)
        {
            scoreValue = points;
            impulse = bounceImpulse;
            hitSound = sound;
        }

        private void Awake()
        {
            audioSource = GetComponent<AudioSource>();
            baseScale = transform.localScale;
        }

        private void Update()
        {
            if (pulseTimer <= 0f)
            {
                transform.localScale = baseScale;
                return;
            }

            pulseTimer -= Time.deltaTime;
            transform.localScale = baseScale * pulseScale;
        }

        private void OnCollisionEnter2D(Collision2D collision)
        {
            Rigidbody2D ball = collision.rigidbody;
            if (ball == null || collision.collider.GetComponent<PinballBall>() == null)
            {
                return;
            }

            Vector2 direction = (ball.position - (Vector2)transform.position).normalized;
            ball.AddForce(direction * impulse, ForceMode2D.Impulse);
            PinballGameController.Instance?.AddScore(scoreValue);
            PinballGameController.Instance?.SetStatus($"+{scoreValue} bumper");
            PlaySound();
            pulseTimer = pulseTime;
        }

        private void PlaySound()
        {
            if (hitSound == null)
            {
                return;
            }

            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
            }

            audioSource.PlayOneShot(hitSound);
        }
    }
}
