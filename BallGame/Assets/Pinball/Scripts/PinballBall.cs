using UnityEngine;

namespace BallGame.Pinball
{
    [RequireComponent(typeof(Rigidbody2D))]
    public sealed class PinballBall : MonoBehaviour
    {
        [SerializeField] private float maxSpeed = 22f;
        [SerializeField] private int wallHitScore = 5;

        private Rigidbody2D body2d;

        private void Awake()
        {
            body2d = GetComponent<Rigidbody2D>();
        }

        private void Start()
        {
            PinballGameController.Instance?.RegisterBall(body2d);
        }

        private void FixedUpdate()
        {
            if (body2d.velocity.sqrMagnitude > maxSpeed * maxSpeed)
            {
                body2d.velocity = body2d.velocity.normalized * maxSpeed;
            }
        }

        private void OnCollisionEnter2D(Collision2D collision)
        {
            if (collision.collider.GetComponent<PinballBumper>() == null)
            {
                PinballGameController.Instance?.AddScore(wallHitScore);
            }
        }
    }
}
