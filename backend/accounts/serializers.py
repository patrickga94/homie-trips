from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "name",
            "dietary_restrictions",
        ]
        # Email is the login + invite key; not editable via the profile.
        read_only_fields = ["email"]

    def validate_dietary_restrictions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a list of items.")
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each item must be text.")
            item = item.strip()
            if item:
                cleaned.append(item[:100])
        return cleaned[:30]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "preferred_name", "password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        # Registration is invite-only: an email may only sign up if a trip
        # member has already invited it (a pending Invitation exists).
        from trips.models import Invitation

        has_invite = Invitation.objects.filter(
            email__iexact=value, status=Invitation.Status.PENDING
        ).exists()
        if not has_invite:
            raise serializers.ValidationError(
                "This email hasn't been invited yet. Ask a trip member to add "
                "you to a trip first, then register with that same email."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs
