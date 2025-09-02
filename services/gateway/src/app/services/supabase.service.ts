import { Injectable } from '@nestjs/common';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class SupabaseService {
  private supabase: SupabaseClient;

  constructor(private configService: ConfigService) {
    const supabaseUrl = this.configService.get<string>('VITE_SUPABASE_URL');
    const supabaseKey = this.configService.get<string>('SUPABASE_SERVICE_ROLE_KEY');

    if (!supabaseUrl || !supabaseKey) {
      throw new Error('Supabase configuration is missing. Please check your environment variables.');
    }

    this.supabase = createClient(supabaseUrl, supabaseKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });
  }

  getClient(): SupabaseClient {
    return this.supabase;
  }

  // Helper method for authenticated operations
  async getAuthenticatedClient(token: string): Promise<SupabaseClient> {
    const client = createClient(
      this.configService.get<string>('VITE_SUPABASE_URL')!,
      this.configService.get<string>('VITE_SUPABASE_ANON_KEY')!
    );

    await client.auth.setSession({
      access_token: token,
      refresh_token: '',
    });

    return client;
  }
}